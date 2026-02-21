"""Platforma sensor pentru integrarea CNAIR eRovinieta."""

import logging
import time
from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CONF_ISTORIC_TRANZACTII,
    DOMAIN,
    ISTORIC_TRANZACTII_DEFAULT,
)
from .coordinator import ErovinietaCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configurează entitățile senzorului pe baza unei intrări de configurare."""
    coordinator: ErovinietaCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    sensors: list[SensorEntity] = []
    _LOGGER.debug(
        "Începem configurarea senzorilor pentru entry_id: %s", config_entry.entry_id
    )

    if not coordinator.data:
        _LOGGER.error(
            "Datele de la coordinator sunt indisponibile. Nu se pot crea senzori."
        )
        return

    # Senzor pentru utilizator
    try:
        sensors.append(DateUtilizatorSensor(coordinator, config_entry))
        _LOGGER.debug("Senzor DateUtilizatorSensor creat cu succes.")
    except Exception as e:
        _LOGGER.error("Eroare la crearea senzorului DateUtilizatorSensor: %s", e)

    # Senzori pentru vehicule
    paginated_data = coordinator.data.get("paginated_data", {}).get("view", [])
    if paginated_data:
        _LOGGER.debug("Găsite %d vehicule în datele paginate.", len(paginated_data))
        for vehicul in paginated_data:
            plate_no = vehicul.get("entity", {}).get("plateNo", "Necunoscut")
            try:
                vin = vehicul.get("entity", {}).get("vin", "Necunoscut")
                certificate_series = vehicul.get("entity", {}).get(
                    "certificateSeries", "Necunoscut"
                )

                if not vin or not plate_no or not certificate_series:
                    _LOGGER.warning(
                        "Vehicul cu date incomplete: VIN=%s, PlateNo=%s, CertificateSeries=%s",
                        vin,
                        plate_no,
                        certificate_series,
                    )
                    continue

                sensors.append(VehiculSensor(coordinator, config_entry, vehicul))
                _LOGGER.debug(
                    "Senzor VehiculSensor creat pentru vehiculul cu număr: %s",
                    plate_no,
                )

                sensors.append(
                    PlataTreceriPodSensor(
                        coordinator,
                        config_entry,
                        vin=vin,
                        plate_no=plate_no,
                        certificate_series=certificate_series,
                    )
                )
                _LOGGER.debug(
                    "Senzor PlataTreceriPodSensor creat pentru vehiculul cu număr: %s",
                    plate_no,
                )

                sensors.append(
                    TreceriPodSensor(
                        coordinator,
                        config_entry,
                        vin=vin,
                        plate_no=plate_no,
                        certificate_series=certificate_series,
                    )
                )
                _LOGGER.debug(
                    "Senzor TreceriPodSensor creat pentru vehiculul cu număr: %s",
                    plate_no,
                )

                sensors.append(SoldSensor(coordinator, config_entry, plate_no))
                _LOGGER.debug(
                    "Senzor SoldSensor creat pentru vehiculul cu număr: %s", plate_no
                )

            except Exception as e:
                _LOGGER.error(
                    "Eroare la crearea senzorilor pentru vehiculul %s: %s",
                    plate_no,
                    e,
                )
    else:
        _LOGGER.warning("Nu au fost găsite vehicule în datele paginate.")

    # Senzor pentru raport tranzacții
    tranzactii_data = coordinator.data.get("transactions", [])
    if tranzactii_data:
        _LOGGER.debug(
            "Găsite %d tranzacții în datele disponibile.", len(tranzactii_data)
        )
        try:
            sensors.append(RaportTranzactiiSensor(coordinator, config_entry))
            _LOGGER.debug("Senzor RaportTranzactiiSensor creat cu succes.")
        except Exception as e:
            _LOGGER.error(
                "Eroare la crearea senzorului RaportTranzactiiSensor: %s", e
            )
    else:
        _LOGGER.warning("Nu au fost găsite tranzacții în datele furnizate.")

    if sensors:
        async_add_entities(sensors)
        _LOGGER.info("Toți senzorii au fost adăugați cu succes.")
    else:
        _LOGGER.warning("Nu au fost creați senzori din cauza lipsei datelor relevante.")


# -------------------------------------------------------------------
#                           Baza
# -------------------------------------------------------------------


class ErovinietaBaseSensor(CoordinatorEntity, SensorEntity):
    """Clasa de bază pentru senzorii Erovinieta."""

    _attr_has_entity_name = True

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

        _LOGGER.debug(
            "Inițializare ErovinietaBaseSensor: name=%s, unique_id=%s",
            self._attr_name,
            self._attr_unique_id,
        )

    @property
    def device_info(self):
        """Informații despre dispozitiv pentru integrare."""
        return {
            "identifiers": {(DOMAIN, self._config_entry.entry_id)},
            "name": "CNAIR eRovinieta",
            "manufacturer": "Ciprian Nicolae (cnecrea)",
            "model": "CNAIR eRovinieta",
            "entry_type": DeviceEntryType.SERVICE,
        }


# -------------------------------------------------------------------
#                     DateUtilizatorSensor
# -------------------------------------------------------------------


class DateUtilizatorSensor(ErovinietaBaseSensor):
    """Senzor pentru afișarea datelor utilizatorului."""

    def __init__(self, coordinator: ErovinietaCoordinator, config_entry: ConfigEntry):
        """Inițializează senzorul DateUtilizatorSensor."""
        user_data = coordinator.data.get("user_data", {})
        utilizator_data = user_data.get("utilizator", {})
        user_identifier = (
            utilizator_data.get("nume", "necunoscut").replace(" ", "_").lower()
        )

        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name="Date utilizator",
            unique_id=f"{DOMAIN}_date_utilizator_{user_identifier}_{config_entry.entry_id}",
            icon="mdi:account-details",
        )

    @property
    def state(self):
        """Returnează starea senzorului (atribut principal)."""
        if not self.coordinator.data or "user_data" not in self.coordinator.data:
            return "nespecificat"

        user_data = self.coordinator.data["user_data"]
        user_id = user_data.get("id")
        return user_id if user_id is not None else "nespecificat"

    @property
    def extra_state_attributes(self):
        """Returnează atributele suplimentare."""
        if not self.coordinator.data or "user_data" not in self.coordinator.data:
            return {}

        user_data = self.coordinator.data["user_data"]
        utilizator_data = user_data.get("utilizator", {})
        tara_data = user_data.get("tara", {})
        denumire_tara = tara_data.get("denumire", "nespecificat")

        def safe_get(data, key, default="nespecificat"):
            value = data.get(key)
            return value if value is not None else default

        def capitalize_name(name):
            return " ".join(word.capitalize() for word in name.split())

        if denumire_tara.lower() == "romania":
            judet = safe_get(user_data.get("judet", {}), "nume")
            localitate = safe_get(user_data.get("localitate", {}), "nume")
        else:
            judet = safe_get(user_data, "judetText")
            localitate = safe_get(user_data, "localitateText")

        attributes = {
            "Numele și prenumele": safe_get(utilizator_data, "nume", "").title(),
            "CNP": safe_get(user_data, "cnpCui"),
            "Telefon de contact": safe_get(utilizator_data, "telefon"),
            "Persoană fizică": "Da" if safe_get(user_data, "pf") else "Nu",
            "Email utilizator": safe_get(utilizator_data, "email"),
            "Acceptă corespondența": (
                "Da" if safe_get(user_data, "acceptaCorespondenta") else "Nu"
            ),
            "Adresa": safe_get(user_data, "adresa"),
            "Localitate": localitate,
            "Județ": judet,
            "Țară": capitalize_name(denumire_tara),
            "attribution": ATTRIBUTION,
        }
        return attributes


# -------------------------------------------------------------------
#                     VehiculSensor
# -------------------------------------------------------------------


class VehiculSensor(ErovinietaBaseSensor):
    """Senzor pentru un vehicul în sistemul e-Rovinietă."""

    def __init__(
        self,
        coordinator: ErovinietaCoordinator,
        config_entry: ConfigEntry,
        vehicul_data: dict,
    ):
        """Inițializează senzorul pentru un vehicul specific."""
        plate_no = vehicul_data.get("entity", {}).get("plateNo", "Necunoscut")
        sanitized = plate_no.replace(" ", "_").lower()

        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name=f"Rovinietă activă ({plate_no})",
            unique_id=f"{DOMAIN}_vehicul_{sanitized}_{config_entry.entry_id}",
            icon="mdi:car",
        )

        self.vehicul_data = vehicul_data
        self.plate_no = plate_no

    @staticmethod
    def get_country_name(country_id, countries_data):
        """Returnează denumirea țării pe baza ID-ului."""
        if not country_id or not countries_data:
            return "Necunoscut"
        for country in countries_data:
            if country.get("id") == country_id:
                country_name = country.get("denumire", "Necunoscut")
                return " ".join(word.capitalize() for word in country_name.split())
        return "Necunoscut"

    @staticmethod
    def format_timestamp(timestamp_millis):
        """Formatează un timestamp (în milisecunde) în format YYYY-MM-DD HH:MM:SS."""
        if timestamp_millis:
            try:
                dt = datetime.fromtimestamp(timestamp_millis / 1000)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except (OSError, ValueError):
                return "Dată invalidă"
        return ""

    @property
    def state(self):
        """Returnează dacă vehiculul are rovinietă activă: Da sau Nu."""
        vignettes_list = self.vehicul_data.get("userDetailsVignettes", [])
        if not vignettes_list:
            return "Nu"

        vignette = vignettes_list[0]
        stop_ts = vignette.get("vignetteStopDate")
        if stop_ts is None:
            return "Nu"

        now_ms = int(time.time() * 1000)
        return "Da" if stop_ts > now_ms else "Nu"

    @property
    def extra_state_attributes(self):
        """Returnează atributele suplimentare ale senzorului."""
        entity = self.vehicul_data.get("entity", {})
        vignettes_list = self.vehicul_data.get("userDetailsVignettes", [])

        attributes = {
            "Număr de înmatriculare": entity.get("plateNo", "Necunoscut"),
            "VIN": entity.get("vin", "Necunoscut"),
            "Seria certificatului": entity.get("certificateSeries", "Necunoscut"),
            "Țara": self.get_country_name(
                entity.get("tara"),
                self.coordinator.data.get("countries_data", []),
            ),
            "attribution": ATTRIBUTION,
        }

        if not vignettes_list:
            attributes["Rovinietă"] = "Nu există rovinietă"
        else:
            vignette = vignettes_list[0]
            start_ts = vignette.get("vignetteStartDate")
            stop_ts = vignette.get("vignetteStopDate")

            start_date_str = self.format_timestamp(start_ts)
            stop_date_str = self.format_timestamp(stop_ts)

            zile_ramase = None
            if stop_ts:
                now_seconds = int(time.time())
                stop_seconds = stop_ts // 1000
                days_diff = (stop_seconds - now_seconds) // 86400
                zile_ramase = days_diff

            attributes["Categorie vignietă"] = vignette.get(
                "vignetteCategory", "Necunoscut"
            )
            attributes["Data început vignietă"] = start_date_str
            attributes["Data sfârșit vignietă"] = stop_date_str
            attributes["Expiră peste (zile)"] = (
                zile_ramase if zile_ramase is not None else "N/A"
            )

        return attributes


# -------------------------------------------------------------------
#                     Senzor RaportTranzactiiSensor
# -------------------------------------------------------------------


class RaportTranzactiiSensor(ErovinietaBaseSensor):
    """Senzor pentru afișarea raportului tranzacțiilor."""

    def __init__(self, coordinator: ErovinietaCoordinator, config_entry: ConfigEntry):
        """Inițializează senzorul RaportTranzactiiSensor."""
        user_data = coordinator.data.get("user_data", {})
        utilizator_data = user_data.get("utilizator", {})
        user_identifier = (
            utilizator_data.get("nume", "necunoscut").replace(" ", "_").lower()
        )

        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name="Raport tranzacții",
            unique_id=f"{DOMAIN}_raport_tranzactii_{user_identifier}_{config_entry.entry_id}",
            icon="mdi:chart-bar-stacked",
        )

    @property
    def state(self):
        """Returnează numărul total al tranzacțiilor realizate."""
        tranzactii_data = self.coordinator.data.get("transactions", [])
        return len(tranzactii_data)

    @property
    def extra_state_attributes(self):
        """Returnează atributele suplimentare simplificate."""
        tranzactii_data = self.coordinator.data.get("transactions", [])
        total_sum = sum(
            float(item.get("valoareTotalaCuTva", 0))
            for item in tranzactii_data
            if isinstance(item, dict)
        )

        years_analyzed = self._config_entry.options.get(
            CONF_ISTORIC_TRANZACTII, ISTORIC_TRANZACTII_DEFAULT
        )
        attributes = {
            "Perioadă analizată": f"Ultimii {years_analyzed} ani",
            "Număr facturi": len(tranzactii_data),
            "Suma totală plătită": f"{total_sum:.2f} RON",
            "attribution": ATTRIBUTION,
        }
        return attributes


# -------------------------------------------------------------------
#             Senzor PlataTreceriPodSensor - restanțe
# -------------------------------------------------------------------


class PlataTreceriPodSensor(ErovinietaBaseSensor):
    """Senzor pentru verificarea plăților pentru treceri de pod (restanțe).

    CORECȚIE CRITICĂ: Filtrarea se face acum per vehicul (vin + plate_no),
    nu la nivel de cont. Anterior, orice trecere neplătită de oricare vehicul
    din cont seta „Da" pentru TOATE vehiculele.
    """

    def __init__(
        self,
        coordinator: ErovinietaCoordinator,
        config_entry: ConfigEntry,
        vin: str,
        plate_no: str,
        certificate_series: str,
    ):
        """Inițializează senzorul PlataTreceriPodSensor."""
        sanitized = plate_no.replace(" ", "_").lower()
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name=f"Restanțe treceri pod ({plate_no})",
            unique_id=f"{DOMAIN}_plata_treceri_pod_{sanitized}_{config_entry.entry_id}",
            icon="mdi:invoice-text-remove",
        )
        self.vin = vin
        self.plate_no = plate_no
        self.certificate_series = certificate_series

    def _get_vehicle_detections(self) -> list:
        """Returnează lista de detecții DOAR pentru acest vehicul.

        Folosește dicționarul per-vehicul din coordinator dacă e disponibil,
        cu fallback pe filtrare din lista consolidată.
        """
        # Preferăm dicționarul per-vehicul (mai eficient, fără ambiguitate)
        per_vehicul = self.coordinator.data.get("treceri_pod_per_vehicul", {})
        if per_vehicul and self.plate_no in per_vehicul:
            return per_vehicul[self.plate_no]

        # Fallback: filtrare din lista consolidată
        return [
            detection
            for detection in self.coordinator.data.get("detectionList", [])
            if detection.get("vin") == self.vin
            and detection.get("plateNo") == self.plate_no
        ]

    @property
    def state(self):
        """Returnează starea principală: Da sau Nu (există restanțe pentru ACEST vehicul?)."""
        detection_list = self._get_vehicle_detections()
        now = int(datetime.now().timestamp() * 1000)
        interval_ms = 24 * 60 * 60 * 1000  # 24 ore în milisecunde

        neplatite = [
            detection
            for detection in detection_list
            if detection.get("paymentStatus") is None
            and now - detection.get("detectionTimestamp", 0) <= interval_ms
        ]
        return "Da" if len(neplatite) > 0 else "Nu"

    @property
    def extra_state_attributes(self):
        """Returnează detalii despre trecerile neplătite (restanțe) pentru ACEST vehicul."""
        detection_list = self._get_vehicle_detections()
        now = int(datetime.now().timestamp() * 1000)
        interval_ms = 24 * 60 * 60 * 1000

        neplatite = [
            detection
            for detection in detection_list
            if detection.get("paymentStatus") is None
            and now - detection.get("detectionTimestamp", 0) <= interval_ms
        ]

        attributes = {
            "Număr treceri neplătite": len(neplatite),
            "Număr de înmatriculare": self.plate_no,
            "VIN": self.vin,
            "Seria certificatului": self.certificate_series,
        }

        def safe_get(value, default=""):
            return value if value is not None else default

        for idx, detection in enumerate(neplatite, start=1):
            timestamp = detection.get("detectionTimestamp")
            formatted_time = (
                datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
                if timestamp
                else ""
            )
            attributes[f"--- Restanțe pentru trecerea de pod #{idx}"] = "\n"
            attributes[f"Trecere {idx} - Categorie"] = safe_get(
                detection.get("detectionCategory")
            )
            attributes[f"Trecere {idx} - Timp detectare"] = formatted_time
            attributes[f"Trecere {idx} - Direcție"] = safe_get(
                detection.get("direction")
            )
            attributes[f"Trecere {idx} - Bandă"] = safe_get(detection.get("lane"))

        attributes["attribution"] = ATTRIBUTION
        return attributes


# -------------------------------------------------------------------
#                Senzor TreceriPodSensor - istoric
# -------------------------------------------------------------------


class TreceriPodSensor(ErovinietaBaseSensor):
    """Senzor pentru afișarea istoriei trecerilor de pod."""

    def __init__(
        self,
        coordinator: ErovinietaCoordinator,
        config_entry: ConfigEntry,
        vin: str,
        plate_no: str,
        certificate_series: str,
    ):
        """Inițializează senzorul TreceriPodSensor."""
        sanitized = plate_no.replace(" ", "_").lower()
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name=f"Treceri pod ({plate_no})",
            unique_id=f"{DOMAIN}_treceri_pod_{sanitized}_{config_entry.entry_id}",
            icon="mdi:bridge",
        )
        self.vin = vin
        self.plate_no = plate_no
        self.certificate_series = certificate_series

    def _get_vehicle_detections(self) -> list:
        """Returnează lista de detecții DOAR pentru acest vehicul."""
        per_vehicul = self.coordinator.data.get("treceri_pod_per_vehicul", {})
        if per_vehicul and self.plate_no in per_vehicul:
            return per_vehicul[self.plate_no]

        return [
            detection
            for detection in self.coordinator.data.get("detectionList", [])
            if detection.get("vin") == self.vin
            and detection.get("plateNo") == self.plate_no
        ]

    @property
    def state(self):
        """Returnează numărul total al trecerilor pentru vehicul."""
        return len(self._get_vehicle_detections())

    @property
    def extra_state_attributes(self):
        """Returnează detalii suplimentare despre treceri."""
        detection_list = self._get_vehicle_detections()

        attributes = {
            "Număr total treceri": len(detection_list),
            "Număr de înmatriculare": self.plate_no,
            "VIN": self.vin,
            "Seria certificatului": self.certificate_series,
        }

        for idx, detection in enumerate(detection_list, start=1):
            timestamp = detection.get("detectionTimestamp")
            formatted_time = (
                datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
                if timestamp
                else ""
            )
            attributes[f"--- Detalii privind trecerea de pod #{idx}"] = "\n"
            attributes[f"Trecere {idx} - Categorie"] = (
                detection.get("detectionCategory") or ""
            )
            attributes[f"Trecere {idx} - Timp detectare"] = formatted_time
            attributes[f"Trecere {idx} - Direcție"] = (
                detection.get("direction") or ""
            )
            attributes[f"Trecere {idx} - Bandă"] = detection.get("lane") or ""
            attributes[f"Trecere {idx} - Valoare (RON)"] = (
                detection.get("value") or ""
            )
            attributes[f"Trecere {idx} - Partener"] = (
                detection.get("partner") or ""
            )
            attributes[f"Trecere {idx} - Metodă plată"] = (
                detection.get("paymentMethod") or ""
            )
            attributes[f"Trecere {idx} - Vehicul"] = (
                detection.get("paymentPlateNo") or ""
            )
            attributes[f"Trecere {idx} - Treceri achiziționate"] = (
                detection.get("taxName") or ""
            )
            valid_until_timestamp = detection.get("validUntilTimestamp")
            formatted_valid_until = (
                datetime.fromtimestamp(valid_until_timestamp / 1000).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                if valid_until_timestamp
                else ""
            )
            attributes[f"Trecere {idx} - Valabilitate până la"] = (
                formatted_valid_until
            )

        attributes["attribution"] = ATTRIBUTION
        return attributes


# -------------------------------------------------------------------
#                Senzor SoldSensor
# -------------------------------------------------------------------


class SoldSensor(ErovinietaBaseSensor):
    """Senzor pentru afișarea soldului 'soldPeajeNeexpirate'."""

    def __init__(
        self,
        coordinator: ErovinietaCoordinator,
        config_entry: ConfigEntry,
        plate_no: str,
    ):
        """Inițializează senzorul SoldSensor."""
        sanitized = plate_no.replace(" ", "_").lower()

        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name=f"Sold peaje neexpirate ({plate_no})",
            unique_id=f"{DOMAIN}_sold_peaje_neexpirate_{sanitized}_{config_entry.entry_id}",
            icon="mdi:boom-gate",
        )
        self.plate_no = plate_no

    @property
    def state(self):
        """Returnează valoarea principală: soldPeajeNeexpirate."""
        paginated_data = self.coordinator.data.get("paginated_data", {}).get(
            "view", []
        )
        if not paginated_data:
            return 0

        for item in paginated_data:
            entity = item.get("entity", {})
            if entity and entity.get("plateNo") == self.plate_no:
                detection_payment_sum = item.get("detectionPaymentSum", {})
                if detection_payment_sum:
                    return detection_payment_sum.get("soldPeajeNeexpirate", 0)
        return 0

    @property
    def extra_state_attributes(self):
        """Returnează atributele suplimentare ale senzorului."""
        paginated_data = self.coordinator.data.get("paginated_data", {}).get(
            "view", []
        )
        attributes = {"attribution": ATTRIBUTION}

        if not paginated_data:
            attributes["Sold peaje neexpirate"] = 0
            return attributes

        for item in paginated_data:
            entity = item.get("entity", {})
            if entity and entity.get("plateNo") == self.plate_no:
                detection_payment_sum = item.get("detectionPaymentSum", {})
                if detection_payment_sum:
                    attributes["Sold peaje neexpirate"] = (
                        detection_payment_sum.get("soldPeajeNeexpirate", 0)
                    )
                    return attributes

        attributes["Sold peaje neexpirate"] = 0
        return attributes
