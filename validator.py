import re

def validate_pattern(regex_pattern: str, sample_logs: list[str]) -> float:
    """
    Validates a regex pattern against a list of sample logs.
    Returns the match rate as a float between 0.0 and 1.0.
    """
    if not sample_logs:
        return 0.0
        
    try:
        compiled_regex = re.compile(regex_pattern)
    except re.error as e:
        print(f"Invalid regex generated: {e}")
        return 0.0
        
    match_count = 0
    for log in sample_logs:
        if compiled_regex.match(log):
            match_count += 1
            
    return match_count / len(sample_logs)
