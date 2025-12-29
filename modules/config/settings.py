import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from ..custom_errors import ConfigurationError

@dataclass
class LLMConfig:
    """Configuration for LLM client"""
    api_key: str
    model: str = "gpt-4.1-mini"
    base_url: Optional[str] = None
    timeout: int = 60
    max_retries: int = 3

    def validate(self) -> None:
        if not self.api_key:
            raise ConfigurationError("API key is required")


@dataclass
class SearchConfig:
    """Configuration for search tool"""
    api_key: str
    base_url: str = "https://api.tavily.com/search"
    timeout: int = 30
    max_retries: int = 3
    exclude_domains: List[str] = field(default_factory=list)
    include_domains: List[str] = field(default_factory=lambda: [
        "abyssinialaw.com", "aera.gov.in", "aerb.gov.in", "africanlii.org", "aftdelhi.nic.in",
        "allahabadhighcourt.in", "amsshardul.com", "aphc.gov.in", "aptel.gov.in", "arbitratead.ae",
        "asianlii.org", "asil.org", "asser.nl", "atfp.gov.in", "austlii.edu.au", "avalon.law.yale.edu",
        "azbpartners.com", "bailii.org", "bananaip.com", "blogs.law.ox.ac.uk", "bombayhighcourt.nic.in",
        "boutique-dalloz.fr", "calcuttahighcourt.gov.in", "canlii.org", "case.law", "caselaw.nationalarchives.gov.uk",
        "cci.gov.in", "cdsco.gov.in", "cea.nic.in", "cercind.gov.in", "cestat.gov.in", "cgat.gov.in",
        "cgit.labour.gov.in", "clc.gov.in", "clpr.org.in", "coe.int", "commerce.gov.in", "commonlii.org",
        "cylaw.org", "cyrilshroff.com", "decisions.scc-csc.ca", "delhidistrictcourts.nic.in", "delhihighcourt.nic.in",
        "dgca.gov.in", "dgms.gov.in", "difccourts.ae", "districts.ecourts.gov.in", "doj.gov.in", "droit.org",
        "drt.gov.in", "dsklegal.com", "eci.gov.in", "ecommitteesci.gov.in", "ecourts.gov.in", "egazette.nic.in",
        "ejil.org", "elegislation.gov.hk", "elplaw.in", "epfindia.gov.in", "eur-lex.europa.eu", "finmin.gov.in",
        "freelaw.in", "fssai.gov.in", "ghconline.gov.in", "globalarbitrationreview.com", "goidirectory.gov.in",
        "gov.uk", "greentribunal.gov.in", "guides.ll.georgetown.edu", "guides.loc.gov", "gujarathighcourt.nic.in",
        "harvardlawreview.org", "hcmadras.tn.gov.in", "hcmimphal.nic.in", "hcraj.nic.in", "hcs.gov.in",
        "highcourt.cg.gov.in", "highcourt.hp.gov.in", "highcourt.kerala.gov.in", "highcourtchd.gov.in",
        "highcourtofuttarakhand.gov.in", "hklii.org", "hollis.harvard.edu", "housing.gov.in", "ibbi.gov.in",
        "icc-cpi.int", "iccwbo.org", "iclg.com", "icrc.org", "icsi.edu", "ifsca.gov.in", "igsg.cnr.it",
        "ikigailaw.com", "ilo.org", "imf.org", "india.gov.in", "indiacode.nic.in", "innertemplelibrary.com",
        "institutrobertbadinter.fr", "internationalcompetitionnetwork.org", "ipindia.gov.in", "irdai.gov.in",
        "itat.gov.in", "jade.io", "jgu.edu.in", "jharkhandhighcourt.nic.in", "jkhighcourt.nic.in", "jsalaw.com",
        "judgments.ecourts.gov.in", "judiciary.karnataka.gov.in", "jura.uni-saarland.de", "juridicas.unam.mx",
        "jurisguide.univ-paris1.fr", "justia.com", "justice.gouv.fr", "justice.govt.nz", "kandspartners.com",
        "kenyalaw.org", "klri.re.kr", "labour.gov.in", "labourbureau.gov.in", "law.asia", "law.cornell.edu",
        "law.ox.ac.uk", "lawcommissionofindia.nic.in", "lawmin.gov.in", "lawphil.net", "laws.africa",
        "legal-tools.org", "legal.un.org", "legalabbrevs.cardiff.ac.uk", "legalref.judiciary.hk", "legifrance.gouv.fr",
        "legislation.govt.nz", "legislationline.org", "lexology.com", "lieber.westpoint.edu", "lii-austria.org",
        "liiofindia.org", "luthra.com", "malawilii.org", "mca.gov.in", "meghalayahighcourt.nic.in", "mondaq.com",
        "mphc.gov.in", "nabard.org", "ncdrc.nic.in", "nclat.nic.in", "nclt.gov.in", "newyorkconvention.org",
        "nfra.gov.in", "nhb.org.in", "nhrc.nic.in", "nishithdesai.com", "njdg.ecourts.gov.in",
        "nliulawreview.nliu.ac.in",
        "nls.ac.in", "nlsir.com", "nlujlawreview.in", "nmc.org.in", "nppaindia.nic.in", "nslr.in", "nujslawreview.org",
        "nurembergacademy.org", "nyulawglobal.org", "oas.org", "orissahighcourt.nic.in", "paclii.org",
        "patnahighcourt.gov.in", "peacepalacelibrary.nl", "pfrda.org.in", "pngrb.gov.in", "prsindia.org",
        "pudr.org", "rbi.org.in", "rct.indianrail.gov.in", "remfry.com", "repository.nls.ac.in",
        "resources.ials.sas.ac.uk", "saflii.org", "samlii.org", "sansad.nic.in", "satweb.sat.gov.in",
        "scobserver.in", "sebi.gov.in", "seylii.org", "siac.org.sg", "sierralii.org", "site.unibo.it",
        "spicyip.com", "sso.agc.gov.sg", "supremecourt.gov", "tariffauthority.gov.in", "tdsat.gov.in",
        "thc.nic.in", "trai.gov.in", "trustbridge.in", "tshc.gov.in", "uaelegislation.gov.ae", "un.org",
        "uncitral.un.org", "unctad.org", "upsc.gov.in", "vidhilegalpolicy.in", "wdra.gov.in", "wipo.int",
        "worldtradelaw.net", "wto.org", "yalelawjournal.org"
    ])

    def validate(self) -> None:
        """Validate search configuration"""
        if not self.api_key:
            raise ConfigurationError("Search API key is required")
        if not self.base_url:
            raise ConfigurationError("Search base URL is required")

@dataclass
class URLValidatorConfig:
    """Configuration for URL validator"""

    timeout: int = 10
    max_retries: int = 2
    preview_chars: int = 500
    user_agent: str = "DeepResearchAgent/1.0"

    def validate(self) -> None:
        """Validate URL validator configuration"""
        if self.timeout < 5:
            raise ConfigurationError("Timeout must be at least 5 seconds")

@dataclass
class DatabaseConfig:
    """Configuration for database connection"""
    mongo_uri: str = "mongodb://localhost:27017"
    database_name: str = "DeepStuff"
    queries_collection: str = "DR_chats"
    sessions_collection: str = "chat_sessions"

    def validate(self) -> None:
        """Validate database configuration"""
        if not self.mongo_uri:
            raise ConfigurationError("MongoDB URI is required")

@dataclass
class ResearchConfig:
    """Main configuration for the research system"""
    llm: LLMConfig
    search: SearchConfig
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    url_validator: URLValidatorConfig = field(default_factory=URLValidatorConfig)

    # Research behavior settings
    normal_mode_steps: int = 3
    detailed_mode_steps: int = 7
    normal_mode_sources: int = 5
    detailed_mode_sources: int = 10
    max_citation_sources: int = 20

    # Logging and debugging
    enable_logging: bool = True
    log_level: str = "INFO"
    debug_mode: bool = False

    def validate(self) -> None:
        """Validate all configurations"""
        self.llm.validate()
        self.search.validate()
        self.database.validate()
        self.url_validator.validate()

    @classmethod
    def from_env(cls) -> 'ResearchConfig':
        """Create configuration from environment variables"""
        openai_api_key = os.getenv("OPENAI_API_KEY")
        tavily_api_key = os.getenv("TAVILY_API_KEY")

        if not openai_api_key:
            raise ConfigurationError("OPENAI_API_KEY environment variable is required")
        if not tavily_api_key:
            raise ConfigurationError("TAVILY_API_KEY environment variable is required")

        llm_config = LLMConfig(
            api_key=openai_api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        )

        search_config = SearchConfig(
            api_key=tavily_api_key,
            base_url=os.getenv("TAVILY_BASE_URL", "https://api.tavily.com/search")
        )

        url_validator_config = URLValidatorConfig(
            timeout=int(os.getenv("URL_VALIDATOR_TIMEOUT", "10"))
        )

        database_config = DatabaseConfig(
            mongo_uri=os.getenv("MONGO_URI", "mongodb://localhost:27017")
        )

        config = cls(
            llm=llm_config,
            search=search_config,
            database=database_config,
            url_validator=url_validator_config,
            enable_logging=os.getenv("ENABLE_LOGGING", "true").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            debug_mode=os.getenv("DEBUG_MODE", "false").lower() == "true"
        )

        config.validate()
        return config
