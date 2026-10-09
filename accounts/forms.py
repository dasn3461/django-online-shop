from django import forms
from .models import Account


class RegistrationForm(forms.ModelForm):

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'placeholder': 'Enter Password',
                'class': 'form-control',
            }
        )
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'placeholder': 'Confirm Password',
                'class': 'form-control',
            }
        )
    )

    class Meta:
        model = Account

        fields = [
            'first_name',
            'last_name',
            'phone_number',
            'email',
            'password',
        ]

        widgets = {
            'first_name': forms.TextInput(
                attrs={
                    'placeholder': 'Enter First Name',
                    'class': 'form-control',
                }
            ),

            'last_name': forms.TextInput(
                attrs={
                    'placeholder': 'Enter Last Name',
                    'class': 'form-control',
                }
            ),

            'phone_number': forms.TextInput(
                attrs={
                    'placeholder': 'Enter Phone Number',
                    'class': 'form-control',
                }
            ),

            'email': forms.EmailInput(
                attrs={
                    'placeholder': 'Enter Email Address',
                    'class': 'form-control',
                }
            ),
        }

    def clean(self):

        cleaned_data = super().clean()

        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password != confirm_password:
            raise forms.ValidationError(
                'Password does not match!'
            )

        return cleaned_data