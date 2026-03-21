"""Platforma sensor pentru integrarea CNAIR eRovinieta.

Senzori disponibili:
- DateUtilizatorSensor: date cont utilizator
- VehiculSensor: stare rovinietă per vehicul
- PlataTreceriPodSensor: restanțe treceri pod per vehicul
- TreceriPodSensor: istoric treceri pod per vehicul
- SoldSensor: sold peaje neexpirate per vehicul
- RaportTranzactiiSensor: sumar tranzacții
"""

from __future__ import annotations

import logging
import time

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CONF_ISTORIC_TRANZACTII,
    DOMAIN,
    ISTORIC_TRANZACTII_DEFAULT,
    LICENSE_DATA_KEY,
    MAX_ATTR_TRECERI,
    VERSION,
)
from .coordinator import ErovinietaCoordinator
from .helpers import capitalize_name, format_timestamp_ms, safe_get, sanitize_plate_no

_LOGGER = logging.getLogger(__name__)


# =====================================================================
#  Setup
# =====================================================================


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configurează senzorii pe baza unei intrări de configurare."""
    coordinator: ErovinietaCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    if not coordinator.data:
        _LOGGER.error("Nu există date de la coordinator. Senzorii nu pot fi creați.")
        return

    sensors: list[SensorEntity] = []

    # Senzor utilizator
    sensors.append(DateUtilizatorSensor(coordinator, config_entry))

    # Senzori per vehicul
    paginated = coordinator.data.get("paginated_data", {}).get("view", [])
    for vehicul in paginated:
        entity = vehicul.get("entity", {})
        plate_no = entity.get("plateNo")
        vin = entity.get("vin")
        cert = entity.get("certificateSeries")

        if not all([plate_no, vin, cert]):
            _LOGGER.warning(
                "Date incomplete pentru vehicul: PlateNo=%s, VIN=%s", plate_no, vin
            )
            continue

        sensors.extend(
            [
                VehiculSensor(coordinator, config_entry, plate_no),
                PlataTreceriPodSensor(
                    coordinator, config_entry, vin, plate_no, cert
                ),
                TreceriPodSensor(
                    coordinator, config_entry, vin, plate_no, cert
                ),
                SoldSensor(coordinator, config_entry, plate_no),
            ]
        )

    # Senzor raport tranzacții
    if coordinator.data.get("transactions"):
        sensors.append(RaportTranzactiiSensor(coordinator, config_entry))

    if sensors:
        async_add_entities(sensors)
        _LOGGER.info("Au fost adăugați %d senzori eRovinieta.", len(sensors))


# =====================================================================
#  Clasa de bază
# =====================================================================


class ErovinietaBaseSensor(CoordinatorEntity[ErovinietaCoordinator], SensorEntity):
    """Clasa de bază pentru toți senzorii eRovinieta."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: ErovinietaCoordinator,
        config_entry: ConfigEntry,
        name: str,
        unique_id: str,
        icon: str | None = None,
    ) -> None:
        """Inițializează senzorul de bază."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_icon = icon

    @property
    def _license_valid(self) -> bool:
        """Verifică dacă licența este validă."""
        mgr = self.hass.data.get(DOMAIN, {}).get(LICENSE_DATA_KEY)
        return mgr is not None and mgr.is_valid

    @property
    def device_info(self) -> DeviceInfo:
        """Informații despre dispozitiv.

        IMPORTANT: Device name = "eRovinieta" → entity_id = sensor.erovinieta_*
        (HA generează entity_id din slug(device_name) + slug(entity_name))
        """
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name="CNAIR eRovinieta",
            manufacturer="CNAIR",
            model="eRovinieta",
            sw_version=VERSION,
            entry_type=DeviceEntryType.SERVICE,
        )


# =====================================================================
#  DateUtilizatorSensor
# =====================================================================


class DateUtilizatorSensor(ErovinietaBaseSensor):
    """Senzor cu datele contului utilizatorului."""

    def __init__(
        self, coordinator: ErovinietaCoordinator, config_entry: ConfigEntry
    ) -> None:
        """Inițializare."""
        user_data = coordinator.data.get("user_data", {})
        utilizator = user_data.get("utilizator", {})
        user_id = (
            utilizator.get("nume", "necunoscut").replace(" ", "_").lower()
        )

        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name="Date utilizator",
            unique_id=f"{DOMAIN}_date_utilizator_{user_id}_{config_entry.entry_id}",
            icon="mdi:account-details",
        )

    @property
    def native_value(self) -> str:
        """Returnează ID-ul utilizatorului."""
        if not self._license_valid:
            return "Licență necesară"
        if not self.coordinator.data or "user_data" not in self.coordinator.data:
            return "nespecificat"
        user_data = self.coordinator.data["user_data"]
        user_id = user_data.get("id")
        return str(user_id) if user_id is not None else "nespecificat"

    @property
    def extra_state_attributes(self) -> dict:
        """Atribute suplimentare ale utilizatorului."""
        if not self._license_valid:
            return {"licență": "necesară"}
        if not self.coordinator.data or "user_data" not in self.coordinator.data:
            return {}

        user_data = self.coordinator.data["user_data"]
        utilizator = user_data.get("utilizator", {})
        tara_data = user_data.get("tara", {})
        denumire_tara = tara_data.get("denumire", "nespecificat")

        if denumire_tara.lower() == "romania":
            judet = safe_get(
                user_data.get("judet", {}).get("nume"), "nespecificat"
            )
            localitate = safe_get(
                user_data.get("localitate", {}).get("nume"), "nespecificat"
            )
        else:
            judet = safe_get(user_data.get("judetText"), "nespecificat")
            localitate = safe_get(user_data.get("localitateText"), "nespecificat")

        return {
            "Numele și prenumele": safe_get(
                utilizator.get("nume"), ""
            ).title(),
            "CNP": safe_get(user_data.get("cnpCui"), "nespecificat"),
            "Telefon de contact": safe_get(
                utilizator.get("telefon"), "nespecificat"
            ),
            "Persoană fizică": "Da" if user_data.get("pf") else "Nu",
            "Email utilizator": safe_get(
                utilizator.get("email"), "nespecificat"
            ),
            "Acceptă corespondența": (
                "Da" if user_data.get("acceptaCorespondenta") else "Nu"
            ),
            "Adresa": safe_get(user_data.get("adresa"), "nespecificat"),
            "Localitate": localitate,
            "Județ": judet,
            "Țară": capitalize_name(denumire_tara),
        }


# =====================================================================
#  VehiculSensor
# =====================================================================


class VehiculSensor(ErovinietaBaseSensor):
    """Senzor pentru starea rovinietei unui vehicul.

    CORECȚIE: Datele vehiculului sunt citite din coordinator la fiecare
    actualizare (nu mai folosim referință stale din __init__).
    """

    def __init__(
        self,
        coordinator: ErovinietaCoordinator,
        config_entry: ConfigEntry,
        plate_no: str,
    ) -> None:
        """Inițializare cu numărul de înmatriculare."""
        sanitized = sanitize_plate_no(plate_no)
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name=f"Rovinietă activă ({plate_no})",
            unique_id=f"{DOMAIN}_vehicul_{sanitized}_{config_entry.entry_id}",
            icon="mdi:car",
        )
        self._plate_no = plate_no

    def _get_vehicle_data(self) -> dict:
        """Obține datele actuale ale vehiculului din coordinator."""
        if not self.coordinator.data:
            return {}
        for item in self.coordinator.data.get("paginated_data", {}).get("view", []):
            if item.get("entity", {}).get("plateNo") == self._plate_no:
                return item
        return {}

    @staticmethod
    def _get_country_name(country_id, countries_data: list) -> str:
        """Returnează denumirea țării pe baza ID-ului."""
        if not country_id or not countries_data:
            return "Necunoscut"
        for country in countries_data:
            if country.get("id") == country_id:
                return capitalize_name(
                    country.get("denumire", "Necunoscut")
                )
        return "Necunoscut"

    @property
    def native_value(self) -> str:
        """Returnează 'Da' dacă vehiculul are rovinietă activă, altfel 'Nu'."""
        if not self._license_valid:
            return "Licență necesară"
        vehicle = self._get_vehicle_data()
        vignettes = vehicle.get("userDetailsVignettes", [])
        if not vignettes:
            return "Nu"

        stop_ts = vignettes[0].get("vignetteStopDate")
        if not stop_ts:
            return "Nu"

        now_ms = int(time.time() * 1000)
        return "Da" if stop_ts > now_ms else "Nu"

    @property
    def extra_state_attributes(self) -> dict:
        """Atribute suplimentare ale vehiculului și rovinietei."""
        if not self._license_valid:
            return {"licență": "necesară"}
        vehicle = self._get_vehicle_data()
        entity = vehicle.get("entity", {})
        vignettes = vehicle.get("userDetailsVignettes", [])

        countries = self.coordinator.data.get("countries_data", [])

        attrs = {
            "Număr de înmatriculare": entity.get("plateNo", "Necunoscut"),
            "VIN": entity.get("vin", "Necunoscut"),
            "Seria certificatului": entity.get(
                "certificateSeries", "Necunoscut"
            ),
            "Țara": self._get_country_name(entity.get("tara"), countries),
        }

        if not vignettes:
            attrs["Rovinietă"] = "Nu există rovinietă"
        else:
            v = vignettes[0]
            start_ts = v.get("vignetteStartDate")
            stop_ts = v.get("vignetteStopDate")

            attrs["Categorie vignietă"] = v.get(
                "vignetteCategory", "Necunoscut"
            )
            attrs["Data început vignietă"] = format_timestamp_ms(start_ts)
            attrs["Data sfârșit vignietă"] = format_timestamp_ms(stop_ts)

            if stop_ts and stop_ts > 0:
                now_s = int(time.time())
                days_left = (stop_ts // 1000 - now_s) // 86400
                attrs["Expiră peste (zile)"] = days_left
            else:
                attrs["Expiră peste (zile)"] = "N/A"

        return attrs


# =====================================================================
#  PlataTreceriPodSensor — restanțe
# =====================================================================


class PlataTreceriPodSensor(ErovinietaBaseSensor):
    """Senzor pentru restanțe treceri pod (neplătite în ultimele 24h).

    Filtrarea se face per vehicul (vin + plate_no).
    """

    def __init__(
        self,
        coordinator: ErovinietaCoordinator,
        config_entry: ConfigEntry,
        vin: str,
        plate_no: str,
        certificate_series: str,
    ) -> None:
        """Inițializare."""
        sanitized = sanitize_plate_no(plate_no)
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name=f"Restanțe treceri pod ({plate_no})",
            unique_id=f"{DOMAIN}_plata_treceri_pod_{sanitized}_{config_entry.entry_id}",
            icon="mdi:invoice-text-remove",
        )
        self._vin = vin
        self._plate_no = plate_no
        self._certificate_series = certificate_series

    def _get_vehicle_detections(self) -> list:
        """Returnează detecțiile pentru acest vehicul."""
        if not self.coordinator.data:
            return []
        per_vehicul = self.coordinator.data.get("treceri_pod_per_vehicul", {})
        if self._plate_no in per_vehicul:
            return per_vehicul[self._plate_no]
        return []

    def _get_unpaid_detections(self) -> list:
        """Returnează detecțiile neplătite din ultimele 24h."""
        detections = self._get_vehicle_detections()
        now_ms = int(time.time() * 1000)
        interval_ms = 24 * 60 * 60 * 1000  # 24 ore

        return [
            d
            for d in detections
            if d.get("paymentStatus") is None
            and now_ms - d.get("detectionTimestamp", 0) <= interval_ms
        ]

    @property
    def native_value(self) -> str:
        """'Da' dacă există restanțe, altfel 'Nu'."""
        if not self._license_valid:
            return "Licență necesară"
        return "Da" if self._get_unpaid_detections() else "Nu"

    @property
    def extra_state_attributes(self) -> dict:
        """Detalii restanțe (limitate la MAX_ATTR_TRECERI)."""
        if not self._license_valid:
            return {"licență": "necesară"}
        neplatite = self._get_unpaid_detections()
        total = len(neplatite)

        # Sortăm descrescător și limităm
        neplatite_sorted = sorted(
            neplatite,
            key=lambda d: d.get("detectionTimestamp", 0),
            reverse=True,
        )
        limited = neplatite_sorted[:MAX_ATTR_TRECERI]

        attrs: dict = {
            "Număr treceri neplătite": total,
            "Număr de înmatriculare": self._plate_no,
            "VIN": self._vin,
            "Seria certificatului": self._certificate_series,
        }

        if total > MAX_ATTR_TRECERI:
            attrs["Avertisment"] = (
                f"Se afișează doar cele mai recente {MAX_ATTR_TRECERI} "
                f"din {total} restanțe."
            )

        for idx, detection in enumerate(limited, start=1):
            ts = detection.get("detectionTimestamp")
            attrs[f"--- Restanță #{idx}"] = ""
            attrs[f"Trecere {idx} - Categorie"] = safe_get(
                detection.get("detectionCategory"), ""
            )
            attrs[f"Trecere {idx} - Timp detectare"] = format_timestamp_ms(ts)
            attrs[f"Trecere {idx} - Direcție"] = safe_get(
                detection.get("direction"), ""
            )
            attrs[f"Trecere {idx} - Bandă"] = safe_get(
                detection.get("lane"), ""
            )

        return attrs


# =====================================================================
#  TreceriPodSensor — istoric
# =====================================================================


class TreceriPodSensor(ErovinietaBaseSensor):
    """Senzor pentru istoricul complet al trecerilor de pod."""

    def __init__(
        self,
        coordinator: ErovinietaCoordinator,
        config_entry: ConfigEntry,
        vin: str,
        plate_no: str,
        certificate_series: str,
    ) -> None:
        """Inițializare."""
        sanitized = sanitize_plate_no(plate_no)
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name=f"Treceri pod ({plate_no})",
            unique_id=f"{DOMAIN}_treceri_pod_{sanitized}_{config_entry.entry_id}",
            icon="mdi:bridge",
        )
        self._vin = vin
        self._plate_no = plate_no
        self._certificate_series = certificate_series

    def _get_vehicle_detections(self) -> list:
        """Returnează detecțiile pentru acest vehicul."""
        if not self.coordinator.data:
            return []
        per_vehicul = self.coordinator.data.get("treceri_pod_per_vehicul", {})
        if self._plate_no in per_vehicul:
            return per_vehicul[self._plate_no]
        return []

    @property
    def native_value(self) -> int | str:
        """Numărul total de treceri."""
        if not self._license_valid:
            return "Licență necesară"
        return len(self._get_vehicle_detections())

    @property
    def extra_state_attributes(self) -> dict:
        """Detalii treceri (limitate la MAX_ATTR_TRECERI, cele mai recente)."""
        if not self._license_valid:
            return {"licență": "necesară"}
        detection_list = self._get_vehicle_detections()
        total = len(detection_list)

        sorted_detections = sorted(
            detection_list,
            key=lambda d: d.get("detectionTimestamp", 0),
            reverse=True,
        )
        limited = sorted_detections[:MAX_ATTR_TRECERI]

        attrs: dict = {
            "Număr total treceri": total,
            "Treceri afișate": len(limited),
            "Număr de înmatriculare": self._plate_no,
            "VIN": self._vin,
            "Seria certificatului": self._certificate_series,
        }

        if total > MAX_ATTR_TRECERI:
            attrs["Avertisment"] = (
                f"Se afișează doar cele mai recente {MAX_ATTR_TRECERI} "
                f"din {total} treceri."
            )

        for idx, detection in enumerate(limited, start=1):
            ts = detection.get("detectionTimestamp")
            valid_until = detection.get("validUntilTimestamp")

            attrs[f"--- Trecere #{idx}"] = ""
            attrs[f"Trecere {idx} - Categorie"] = safe_get(
                detection.get("detectionCategory"), ""
            )
            attrs[f"Trecere {idx} - Timp detectare"] = format_timestamp_ms(ts)
            attrs[f"Trecere {idx} - Direcție"] = safe_get(
                detection.get("direction"), ""
            )
            attrs[f"Trecere {idx} - Bandă"] = safe_get(
                detection.get("lane"), ""
            )
            attrs[f"Trecere {idx} - Valoare (RON)"] = safe_get(
                detection.get("value"), ""
            )
            attrs[f"Trecere {idx} - Partener"] = safe_get(
                detection.get("partner"), ""
            )
            attrs[f"Trecere {idx} - Metodă plată"] = safe_get(
                detection.get("paymentMethod"), ""
            )
            attrs[f"Trecere {idx} - Vehicul"] = safe_get(
                detection.get("paymentPlateNo"), ""
            )
            attrs[f"Trecere {idx} - Treceri achiziționate"] = safe_get(
                detection.get("taxName"), ""
            )
            attrs[f"Trecere {idx} - Valabilitate până la"] = (
                format_timestamp_ms(valid_until)
            )

        return attrs


# =====================================================================
#  SoldSensor
# =====================================================================


class SoldSensor(ErovinietaBaseSensor):
    """Senzor pentru soldul peajelor neexpirate."""

    def __init__(
        self,
        coordinator: ErovinietaCoordinator,
        config_entry: ConfigEntry,
        plate_no: str,
    ) -> None:
        """Inițializare."""
        sanitized = sanitize_plate_no(plate_no)
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name=f"Sold peaje neexpirate ({plate_no})",
            unique_id=f"{DOMAIN}_sold_peaje_neexpirate_{sanitized}_{config_entry.entry_id}",
            icon="mdi:boom-gate",
        )
        self._plate_no = plate_no

    def _get_sold(self) -> int | float:
        """Obține soldul din datele coordinator-ului."""
        if not self.coordinator.data:
            return 0
        for item in self.coordinator.data.get("paginated_data", {}).get("view", []):
            entity = item.get("entity", {})
            if entity.get("plateNo") == self._plate_no:
                payment_sum = item.get("detectionPaymentSum", {})
                if payment_sum:
                    return payment_sum.get("soldPeajeNeexpirate", 0)
        return 0

    @property
    def native_value(self) -> int | float | str:
        """Valoarea soldului."""
        if not self._license_valid:
            return "Licență necesară"
        return self._get_sold()

    @property
    def extra_state_attributes(self) -> dict:
        """Atribute suplimentare."""
        if not self._license_valid:
            return {"licență": "necesară"}
        return {
            "Sold peaje neexpirate": self._get_sold(),
        }


# =====================================================================
#  RaportTranzactiiSensor
# =====================================================================


class RaportTranzactiiSensor(ErovinietaBaseSensor):
    """Senzor sumar pentru raportul de tranzacții."""

    def __init__(
        self, coordinator: ErovinietaCoordinator, config_entry: ConfigEntry
    ) -> None:
        """Inițializare."""
        user_data = coordinator.data.get("user_data", {})
        utilizator = user_data.get("utilizator", {})
        user_id = (
            utilizator.get("nume", "necunoscut").replace(" ", "_").lower()
        )

        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name="Raport tranzacții",
            unique_id=f"{DOMAIN}_raport_tranzactii_{user_id}_{config_entry.entry_id}",
            icon="mdi:chart-bar-stacked",
        )

    @property
    def native_value(self) -> int | str:
        """Numărul total de tranzacții."""
        if not self._license_valid:
            return "Licență necesară"
        if not self.coordinator.data:
            return 0
        return len(self.coordinator.data.get("transactions", []))

    @property
    def extra_state_attributes(self) -> dict:
        """Sumar tranzacții."""
        if not self._license_valid:
            return {"licență": "necesară"}
        if not self.coordinator.data:
            return {}

        transactions = self.coordinator.data.get("transactions", [])
        total_sum = sum(
            float(item.get("valoareTotalaCuTva", 0))
            for item in transactions
            if isinstance(item, dict)
        )

        years = self._config_entry.options.get(
            CONF_ISTORIC_TRANZACTII, ISTORIC_TRANZACTII_DEFAULT
        )

        return {
            "Perioadă analizată": f"Ultimii {years} ani",
            "Număr facturi": len(transactions),
            "Suma totală plătită": f"{total_sum:.2f} RON",
        }
