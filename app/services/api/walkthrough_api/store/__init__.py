"""The storage interface (base.py: Store, the store-file records, BlobRef, StagedRef, NotFound) and the local file store
(local.py: LocalStore over app/data), DESIGN.md 9. Routes reach a store only through Depends(get_store)."""
