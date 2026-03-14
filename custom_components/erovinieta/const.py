"""Constante pentru integrarea CNAIR eRovinieta."""

DOMAIN = "erovinieta"
VERSION = "2.3.0"
ATTRIBUTION = "Date furnizate de www.erovinieta.ro"

# URL-urile API-ului
BASE_URL = "https://www.erovinieta.ro/vignettes-portal-web"
URL_LOGIN = f"{BASE_URL}/login"
URL_GET_USER_DATA = f"{BASE_URL}/rest/setariUtilizatorPortal"
URL_GET_PAGINATED = f"{BASE_URL}/rest/desktop/home/getDataPaginated"
URL_GET_COUNTRIES = f"{BASE_URL}/rest/anonymous/getCountries"
URL_TRANZACTII = (
    BASE_URL + "/rest/transaction/getTransaction?"
    "dateFrom={dateFrom}&dateTo={dateTo}&paymentType=2&transactionType=3"
)
URL_DETALII_TRANZACTIE = (
    BASE_URL + "/rest/transaction/getTransactionDetails?"
    "series={series}&transactionType=3"
)
URL_TRECERI_POD = (
    f"{BASE_URL}/rest/anonymous/bridge/detectionsAndPayments/"
    "getDetectionsAndPayments"
)

# Chei de configurare
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_ISTORIC_TRANZACTII = "istoric_tranzactii"

# Valori implicite
DEFAULT_UPDATE_INTERVAL = 3600  # 1 oră (secunde)
MIN_UPDATE_INTERVAL = 300  # 5 minute (secunde)
MAX_UPDATE_INTERVAL = 86400  # 1 zi (secunde)
ISTORIC_TRANZACTII_DEFAULT = 2  # ani

# Limită atribute de stare (previne > 16384 bytes recorder)
MAX_ATTR_TRECERI = 20

# Platforme suportate
PLATFORMS: list[str] = ["sensor"]

# Validitate token (secunde) — puțin sub 1 oră
TOKEN_VALIDITY_SECONDS = 3500
