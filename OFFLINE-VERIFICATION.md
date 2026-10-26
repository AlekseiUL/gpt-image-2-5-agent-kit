# Offline verification boundary

Pinned test dependency constraints and read-only workflow permissions.

## Reproduce

`python -m pip install -c requirements-ci.lock ".[test]"; python -m pytest`

Generation and provider billing are separate opt-in checks, not exercised by the offline suite.

## Rollback

Review the commit diff and use a new checkout of the pre-change commit for source rollback. Keep user data and live installations untouched. A source rollback is not permission to restore unsafe network exposure or bypass approval.
