from gspread_pandas import Spread


def get_spread(sheet_id: str, sheet: str, google_creds) -> Spread:
    return Spread(
        sheet_id,
        creds=google_creds,
        sheet=sheet)
