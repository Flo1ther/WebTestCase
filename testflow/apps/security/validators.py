import re
from django.core.exceptions import ValidationError

class PasswordPolicy:
    def validate(self, password, user=None):
        rules = [
            (len(password) >= 8, 'Щонайменше 8 символів.'),
            (any(c.isupper() for c in password), 'Принаймні одна велика літера.'),
            (any(c.islower() for c in password), 'Принаймні одна мала літера.'),
            (any(c.isdecimal() for c in password), 'Принаймні одна цифра.'),
            (any(not c.isalnum() and not c.isspace() for c in password), 'Принаймні один спеціальний символ.'),
        ]
        errors = [message for valid, message in rules if not valid]
        if len(password) > 128:
            errors.append('Не більше 128 символів.')
        if errors:
            raise ValidationError(errors)
    def get_help_text(self):
        return '8-128 символів, велика та мала літери, цифра і спеціальний символ.'
