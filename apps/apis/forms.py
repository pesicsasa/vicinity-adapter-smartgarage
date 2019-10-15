from django import forms


class GarageForm(forms.Form):
    name = forms.CharField(label='Your full name', max_length=254)
    email = forms.EmailField(label='Email address', max_length=256)
    valid_from = forms.DateTimeField(label='From')
    valid_until = forms.DateTimeField(label='To')

    def clean(self):
        cleaned_data = super(GarageForm, self).clean()
        name = cleaned_data.get('name')
        email = cleaned_data.get('email')
        valid_from = cleaned_data.get('valid_from')
        valid_until = cleaned_data.get('valid_until')
        if not name and not email and not valid_from and not valid_until:
            raise forms.ValidationError('You have to write something!')

