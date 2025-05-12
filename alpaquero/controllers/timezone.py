#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import logging
from collections import OrderedDict

import yaml

from alpaquero.models.timezone import read_regions
from alpaquero.views.timezone import TimezoneView
from .controller import Controller

log = logging.getLogger('controllers.timezone')


class TimezoneController(Controller):
    def __init__(self, app):
        super().__init__(app)
        self._all_regions = OrderedDict()
        for region in read_regions():
            self._all_regions[region.name] = region

        self.region = 'America'
        self.city = 'New_York'

    @property
    def regions(self) -> list[str]:
        return [k for k in self._all_regions.keys()]

    def cities_for_region(self, region: str) -> list[str]:
        return self._all_regions[region].cities

    def make_ui(self):
        return TimezoneView(self, self.region, self.city)

    def done(self, region: str, city: str):
        self.region = region
        self.city = city
        log.debug('Timezone: {}/{}'.format(self.region, self.city))
        self._app.next_screen()

    def cancel(self):
        self._app.prev_screen()

    def to_yaml(self) -> str:
        yaml_data = yaml.dump({'timezone': '{}/{}'.format(self.region, self.city)})
        log.debug('export to yaml: {}'.format(yaml_data))
        return yaml_data
