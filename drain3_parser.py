from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig

# Initialize a global TemplateMiner instance to maintain state across calls
config = TemplateMinerConfig()
config.load("drain3.ini")
template_miner = TemplateMiner(config=config)

def extract_template(raw_log: str) -> dict:
    """
    Extracts a log template from a raw log string using Drain3.
    Returns a dictionary with 'cluster_id' and 'template'.
    """
    result = template_miner.add_log_message(raw_log)
    return {
        "cluster_id": result["cluster_id"],
        "template": result["template_mined"]
    }
