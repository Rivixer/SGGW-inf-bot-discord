class RegistrationError(Exception):
    pass


class RegistrationBlocked(RegistrationError):
    pass


class TooManyRegistrationMails(RegistrationError):

    def __init__(self, old_code: str, *args: object) -> None:
        super().__init__(*args)
        self.old_code = old_code
