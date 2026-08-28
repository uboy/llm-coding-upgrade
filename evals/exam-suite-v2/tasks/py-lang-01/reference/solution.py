class transaction:
    def __init__(self, steps):
        self.steps = steps

    def _rollback(self, done, exc):
        rollback_errors = []
        for undo in reversed(done):
            if undo is None:
                continue
            try:
                undo()
            except Exception as e:
                rollback_errors.append(e)
        if rollback_errors:
            exc.rollback_errors = rollback_errors

    def __enter__(self):
        done = []
        for do, undo in self.steps:
            try:
                do()
            except Exception as exc:
                self._rollback(done, exc)
                raise
            done.append(undo)
        self._done = done
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc is not None:
            self._rollback(self._done, exc)
        return False
