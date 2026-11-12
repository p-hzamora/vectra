"""Bring a collection in line with its source folder."""

from functools import partial

from vectra.bounded_context.retrieval.application.dtos import (
    DocumentIndexResultDTO,
    FileFailureDTO,
    ManifestEntryDTO,
    SourceFileDTO,
    SyncResultDTO,
)
from vectra.bounded_context.retrieval.application.ports.embedding import IEmbedder
from vectra.bounded_context.retrieval.application.ports.progress import IProgress, NullProgress
from vectra.bounded_context.retrieval.application.ports.read_repositories import (
    IManifestReadRepository,
)
from vectra.bounded_context.retrieval.application.ports.source import IDocumentSource
from vectra.bounded_context.retrieval.application.services import (
    CollectionProvisioner,
    DocumentFingerprinter,
    DocumentIndexer,
    DocumentRemover,
    RetryRunner,
)
from vectra.bounded_context.retrieval.domain.entities import Collection
from vectra.bounded_context.retrieval.domain.policies import MassDeletePolicy, SyncPlanningPolicy
from vectra.bounded_context.retrieval.domain.value_objects import (
    CollectionName,
    SourcePath,
    SourceRoot,
    SyncPlan,
)
from vectra.exceptions import MassDeleteRefusedError, SourceRootInvalidError
from vectra.shared_kernel.application.handlers import IHandler
from vectra.utils import FrozenObject

DEFAULT_INCLUDE: tuple[str, ...] = ("**/*.md",)


class SyncCollectionCommand(FrozenObject):
    """Sync a folder into a collection.

    Attributes:
        collection: Collection name; created on first sync.
        root: Absolute path of the source folder; `None` uses the collection's own root.
        include: Glob patterns to index.
        exclude: Glob patterns to skip.
        dry_run: Plan only; write nothing.
        allow_mass_delete: Permit deleting more than half of the indexed documents.
        rebuild: Drop the collection and recreate it with the current profile.
        allow_new_root: With `rebuild`, permit ROOT to differ from the collection's root.
    """

    collection: str
    root: str | None = None
    include: tuple[str, ...] = DEFAULT_INCLUDE
    exclude: tuple[str, ...] = ()
    dry_run: bool = False
    allow_mass_delete: bool = False
    rebuild: bool = False
    allow_new_root: bool = False


class SyncCollectionHandler(IHandler[SyncCollectionCommand, SyncResultDTO]):
    """Scans, plans and applies changes document by document; one failing file never stops the rest."""

    def __init__(
        self,
        *,
        manifest: IManifestReadRepository,
        source: IDocumentSource,
        embedder: IEmbedder,
        provisioner: CollectionProvisioner,
        fingerprinter: DocumentFingerprinter,
        indexer: DocumentIndexer,
        remover: DocumentRemover,
        retry: RetryRunner,
        planning: SyncPlanningPolicy | None = None,
        mass_delete: MassDeletePolicy | None = None,
        progress: IProgress | None = None,
    ) -> None:
        self._manifest: IManifestReadRepository = manifest
        self._source: IDocumentSource = source
        self._embedder: IEmbedder = embedder
        self._provisioner: CollectionProvisioner = provisioner
        self._fingerprinter: DocumentFingerprinter = fingerprinter
        self._indexer: DocumentIndexer = indexer
        self._remover: DocumentRemover = remover
        self._retry: RetryRunner = retry
        self._planning: SyncPlanningPolicy = planning or SyncPlanningPolicy()
        self._mass_delete: MassDeletePolicy = mass_delete or MassDeletePolicy()
        self._progress: IProgress = progress or NullProgress()

    async def handle(self, action: SyncCollectionCommand) -> SyncResultDTO:
        """Sync the collection.

        Raises:
            SourceRootInvalidError: The root is missing, or none was given for a new collection
                (nothing is touched).
            SourceRootInvalidError: The collection is bound to another root (also on rebuild
                unless `allow_new_root`).
            EmbeddingProfileMismatchError: The configured model differs from the collection's.
            MassDeleteRefusedError: More than half of the indexed documents would be deleted
                (not raised on a dry run; it becomes a warning).
        """
        name = CollectionName(value=action.collection)
        collection: Collection | None = await self._provisioner.get(name)
        root: SourceRoot
        if action.root is not None:
            root = SourceRoot(value=action.root)
        elif collection is not None:
            root = collection.source_root
        else:
            raise SourceRootInvalidError(
                f"Collection {name} does not exist, so it has no root to sync.",
                {"collection": name.value},
                next_steps=[f"Run `vectra sync {name.value} ROOT` to create it."],
            )
        self._progress.report(f"{name.value}: scanning {root.value}")
        files: list[SourceFileDTO] = [
            file async for file in self._source.scan(root.value, action.include, action.exclude)
        ]
        if collection is not None:
            if not action.rebuild:
                collection.assert_same_root(root)
                collection.assert_compatible(self._embedder.profile)
            elif not action.allow_new_root:
                collection.assert_same_root(root, rebuild=True)

        scanned, failures = self._fingerprinter.scanned(files)
        entries: list[ManifestEntryDTO] = (
            [] if action.rebuild else [entry async for entry in self._manifest.stream(name.value)]
        )
        plan: SyncPlan = self._planning.plan(scanned, self._fingerprinter.indexed(entries))
        self._progress.report(
            f"{name.value}: {len(files)} files scanned, plan: add {len(plan.add)}, "
            f"update {len(plan.update)}, delete {len(plan.delete)}, "
            f"unchanged {len(plan.unchanged)}"
        )
        refusal: MassDeleteRefusedError | None = self._mass_delete.refusal(
            collection=name.value,
            to_delete=len(plan.delete),
            indexed=len(entries),
            allowed=action.allow_mass_delete,
        )
        if refusal is not None and not action.dry_run:
            raise refusal

        created: bool = collection is None or action.rebuild
        if action.dry_run:
            return SyncResultDTO(
                collection=name.value,
                dry_run=True,
                created=created,
                added=tuple(path.value for path in plan.add),
                updated=tuple(path.value for path in plan.update),
                deleted=tuple(path.value for path in plan.delete),
                unchanged=len(plan.unchanged),
                failed=tuple(failures.values()),
                warnings=(
                    ()
                    if refusal is None
                    else (
                        f"The real sync would be refused ({len(plan.delete)} of {len(entries)} "
                        "indexed documents would be deleted) without --allow-mass-delete.",
                    )
                ),
            )
        if collection is not None and action.rebuild:
            self._progress.report(f"{name.value}: dropping the old index (rebuild)")
            await self._provisioner.drop(name)
        if created:
            await self._provisioner.create(name, root)

        hashes: dict[str, str] = {file.path: file.content_hash for file in files}
        added: list[str] = []
        updated: list[str] = []
        deleted: list[str] = []
        warnings: list[str] = []
        chunks_written: int = 0
        to_index: tuple[SourcePath, ...] = plan.add + plan.update
        if to_index:
            self._progress.report(
                f"{name.value}: embedding with {self._embedder.profile.fingerprint} "
                "(the model loads on the first file)"
            )
        for position, path in enumerate(to_index, start=1):
            indexed: DocumentIndexResultDTO | FileFailureDTO = await self._retry.run(
                path, partial(self._indexer.index, name, root, path, hashes[path.value])
            )
            if isinstance(indexed, FileFailureDTO):
                failures[path.value] = indexed
                self._progress.report(
                    f"[{position}/{len(to_index)}] failed {path.value} [{indexed.code}]"
                )
                continue
            chunks_written += indexed.chunks_written
            warnings.extend(indexed.warnings)
            (added if path in plan.add else updated).append(path.value)
            self._progress.report(
                f"[{position}/{len(to_index)}] {'added' if path in plan.add else 'updated'} "
                f"{path.value} ({indexed.chunks_written} chunks)"
            )
        for position, path in enumerate(plan.delete, start=1):
            removed: FileFailureDTO | None = await self._retry.run(
                path, partial(self._remover.remove, name, path)
            )
            if isinstance(removed, FileFailureDTO):
                failures[path.value] = removed
            else:
                deleted.append(path.value)
                self._progress.report(f"[{position}/{len(plan.delete)}] deleted {path.value}")
        return SyncResultDTO(
            collection=name.value,
            dry_run=False,
            created=created,
            added=tuple(added),
            updated=tuple(updated),
            deleted=tuple(deleted),
            unchanged=len(plan.unchanged),
            failed=tuple(failures.values()),
            warnings=tuple(warnings),
            chunks_written=chunks_written,
        )
