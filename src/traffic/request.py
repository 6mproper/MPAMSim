from src.contracts.transaction import Transaction


# Compatibility import for existing callers. Transaction is the only runtime
# request type; this alias does not create a second data path.
Request = Transaction

__all__ = ["Request", "Transaction"]
