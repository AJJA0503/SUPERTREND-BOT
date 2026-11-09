from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    BINANCE_API_KEY: str = ""
    BINANCE_API_SECRET: str = ""
    BINANCE_TESTNET: bool = True

    GATEIO_API_KEY: str = ""
    GATEIO_API_SECRET: str = ""
    GATEIO_TESTNET: bool = True

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ALLOWED_CHAT_IDS: str = ""

    WEB_HOST: str = "0.0.0.0"
    WEB_PORT: int = 8080
    WEB_AUTH_TOKEN: str = "change_me"

    TZ: str = "UTC"
    LOG_LEVEL: str = "INFO"
    DATA_DIR: str = "./data"
    STATE_DIR: str = "./state"
    CONFIG_DIR: str = "./config"

    @property
    def allowed_chats(self) -> set[int]:
        return {int(x) for x in self.TELEGRAM_ALLOWED_CHAT_IDS.split(",") if x.strip()}

settings = Settings()