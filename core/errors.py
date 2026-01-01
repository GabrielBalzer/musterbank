"""Exceptions raised by the core bank."""


class BankError(Exception):
    pass


class UnknownAccount(BankError):
    pass


class UnknownCustomer(BankError):
    pass


class AccountNotActive(BankError):
    pass


class InsufficientFunds(BankError):
    pass


class InvalidAmount(BankError):
    pass


class InvalidIban(BankError):
    pass


class EodAlreadyRun(BankError):
    pass
