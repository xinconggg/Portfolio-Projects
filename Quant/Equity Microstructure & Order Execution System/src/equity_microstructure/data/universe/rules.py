TIER1_RULE_VERSION = "1.0"

TIER1_ELIGIBLE_SECURITY_TYPES = {
    "EQTY",
}

TIER1_ELIGIBLE_SECURITY_SUBTYPES = {
    "COM",
}


def is_tier1_security(df):
    return (
        df["SecurityType"].isin(TIER1_ELIGIBLE_SECURITY_TYPES)
        & df["SecuritySubType"].isin(TIER1_ELIGIBLE_SECURITY_SUBTYPES)
    )