import urwid

from subiquitycore.view import BaseView
from subiquitycore.ui.form import Form, ChoiceField
from subiquitycore.ui.selector import Option

class TimezoneForm(Form):
    cancel_label = 'Back'

    region = ChoiceField('Region:', choices=['dummy'])
    city = ChoiceField('City:', choices=['dummy'])

class TimezoneView(BaseView):
    title = 'Time zone'
    excerpt = 'Select time zone.'

    def __init__(self, controller, region: str, city: str):
        self._controller = controller

        self._form = TimezoneForm()
        self._init_regions()
        self._set_values(region, city)

        urwid.connect_signal(self._form.region.widget, 'select',
                             self._select_region)

        urwid.connect_signal(self._form, 'submit', self.done)
        urwid.connect_signal(self._form, 'cancel', self.cancel)

        super().__init__(self._form.as_screen(excerpt=self.excerpt,
                                              focus_buttons=True))

    def _init_regions(self):
        reg_opts = []
        for region in self._controller.regions:
            reg_opts.append(Option((region, True, region)))
        self._form.region.widget.options = reg_opts

    def _set_values(self, region: str, city: str):
        if region is None:
            region = self._controller.regions[0]
        self._form.region.widget.value = region

        city_opts = []
        for name in self._controller.cities_for_region(region):
            city_opts.append(Option((name, True, name)))
        self._form.city.widget.options = city_opts
        if city is None:
            self._form.city.widget.index = 0
        else:
            self._form.city.widget.value = city

    def _select_region(self, sender, region: str):
        self._set_values(region, None)

    def done(self, sender):
        self._controller.done(region=self._form.region.widget.value,
                              city=self._form.city.widget.value)

    def cancel(self, sender=None):
        self._controller.cancel()
