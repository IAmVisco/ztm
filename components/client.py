import logging
from datetime import datetime
from typing import Optional, Dict, List

import requests

from .models import ZTMDepartureData, ZTMDepartureDataReading

_LOGGER = logging.getLogger(__name__)


class ZTMStopClient:
    def __init__(self, api_key: str, stop_id: int, stop_number: str, timeout: Optional[int] = None):
        self._endpoint = "https://api.um.warszawa.pl/api/action/dbtimetable_get/"
        self._data_id = "e923fa0e-d96c-43f9-ae6e-60518c9f3238"
        self._timeout = timeout or 10
        self._api_key = api_key
        self._stop_id = stop_id
        self._stop_number = stop_number

    @property
    def id(self):
        return self._data_id

    def get(self, lines: List[int]) -> Dict[int, Optional[ZTMDepartureData]]:
        """
        Fetch departures for the provided line numbers.

        Returns a mapping: line -> ZTMDepartureData (or None on error for that line)
        """
        results: Dict[int, Optional[ZTMDepartureData]] = {}
        for line in lines:
            params = {
                'id': self.id,
                'apikey': self._api_key,
                'busstopId': self._stop_id,
                'busstopNr': self._stop_number,
                'line': line,
            }
            try:
                response = requests.get(self._endpoint, params=params, timeout=self._timeout)
            except requests.RequestException as e:
                _LOGGER.error(f"Cannot connect to ZTM API endpoint. {e}")
                results[line] = None
                continue

            if response.status_code != 200:
                try:
                    err_text = response.text
                except Exception:
                    err_text = ""
                _LOGGER.error(f"Error fetching data: HTTP {response.status_code} {err_text}")
                results[line] = None
                continue

            try:
                json_response = response.json()
            except ValueError:
                _LOGGER.error("Received non-JSON data from ZTM API endpoint")
                results[line] = None
                continue

            _data = {}
            _departures = []

            now = datetime.now().astimezone()
            # Some API responses may include {"result": null}. Ensure we handle that safely.
            result_payload = json_response.get("result")
            if result_payload is None:
                _LOGGER.debug(f"ZTM API returned result=None for line {line} at stop {self._stop_id}/{self._stop_number}")
                result_payload = []
            elif not isinstance(result_payload, list):
                result_payload = []

            for reading in result_payload:
                for entry in reading:
                    _data[entry.get("key")] = entry.get("value")

                try:
                    _departures.append(ZTMDepartureDataReading.from_dict(_data))
                except Exception:
                    _LOGGER.warning(f"Data not matching ZTMDepartureDataReading struct: {_data}")

            departures = list(filter(lambda x: x.dt is not None and x.dt >= now, _departures))
            departures.sort(key=lambda x: x.time_to_depart)
            results[line] = ZTMDepartureData(departures=departures)

        return results
