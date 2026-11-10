"""Collection aggregate root."""

from dataclasses import dataclass
from datetime import datetime

from vectra.bounded_context.retrieval.domain.value_objects import (
    CollectionName,
    EmbeddingProfile,
    SourceRoot,
)
from vectra.exceptions import SourceRootInvalidError


@dataclass(slots=True, kw_only=True)
class Collection:
    """A named index bound to one source root and one immutable embedding profile.

    Attributes:
        name: Identity.
        profile: Model and dimension of its embeddings; never changes.
        source_root: Folder indexed, bound at creation.
        created_at: Creation time.
    """

    name: CollectionName
    profile: EmbeddingProfile
    source_root: SourceRoot
    created_at: datetime

    def assert_compatible(self, profile: EmbeddingProfile) -> None:
        """Fail unless `profile` matches this collection's.

        Raises:
            EmbeddingProfileMismatchError: Model or dimension differs.
        """
        profile.assert_matches(self.profile, self.name.value)

    def assert_same_root(self, root: SourceRoot, *, rebuild: bool = False) -> None:
        """Fail unless `root` is the root this collection was created for.

        Args:
            root: Folder being synced.
            rebuild: The sync is a rebuild; the next steps then mention `--new-root`.

        Raises:
            SourceRootInvalidError: The collection is bound to another root.
        """
        if root != self.source_root:
            raise SourceRootInvalidError(
                f"Collection {self.name} indexes {self.source_root.value}, not {root.value}.",
                {
                    "collection": self.name.value,
                    "bound_root": self.source_root.value,
                    "given_root": root.value,
                },
                next_steps=(
                    [
                        f"Rebuild {self.source_root.value}, or pass --new-root to rebind "
                        f"the collection to {root.value}."
                    ]
                    if rebuild
                    else [f"Sync {self.source_root.value}, or use a different collection name."]
                ),
            )

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Collection) and other.name == self.name

    def __hash__(self) -> int:
        return hash(self.name)
