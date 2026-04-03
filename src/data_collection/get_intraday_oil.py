from pathlib import Path
from datetime import datetime, timedelta, timezone

import pandas as pd
import lseg.data as ld
from lseg.data.content import historical_pricing as hp


def download_intraday_history(
    ric: str,
    outpath: str,
    interval=hp.Intervals.FIVE_MINUTES,
    lookback_days: int = 60,
    chunk_days: int = 1,
) -> pd.DataFrame:
    """
    Download intraday history for one instrument in small chunks and save to CSV.

    Parameters
    ----------
    ric : str
        Instrument RIC, for example "LCOc1" or "CLc1".
    outpath : str
        Output CSV file path.
    interval : hp.Intervals
        Intraday interval, e.g. FIVE_MINUTES or ONE_MINUTE.
    lookback_days : int
        Number of days to look back from now.
    chunk_days : int
        Number of days per API request.

    Returns
    -------
    pd.DataFrame
        Combined dataframe of intraday data.
    """
    Path(outpath).parent.mkdir(parents=True, exist_ok=True)

    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=lookback_days)

    chunks = []

    current_start = start_dt

    while current_start < end_dt:
        current_end = min(current_start + timedelta(days=chunk_days), end_dt)

        print(
            f"Downloading {ric}: "
            f"{current_start.strftime('%Y-%m-%d %H:%M:%S')} UTC "
            f"to {current_end.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

        response = hp.summaries.Definition(
            universe=ric,
            interval=interval,
            start=current_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            end=current_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            fields=[
                "OPEN_PRC",
                "HIGH_1",
                "LOW_1",
                "TRDPRC_1",
                "ACVOL_UNS",
            ],
        ).get_data()

        df_chunk = response.data.df.copy()

        if not df_chunk.empty:
            chunks.append(df_chunk)

        current_start = current_end

    if not chunks:
        raise ValueError(f"No data returned for {ric}. Check the RIC and your entitlements.")

    df = pd.concat(chunks)
    df = df[~df.index.duplicated(keep="first")]
    df = df.sort_index()

    df.to_csv(outpath)
    print(f"Saved {len(df)} rows to {outpath}")

    return df


def main() -> None:
    instruments = {
        "LCOc1": "data/raw/oil/brent_LCOc1_last_2_months_5min.csv",
        "CLc1": "data/raw/oil/wti_CLc1_last_2_months_5min.csv",
    }

    ld.open_session()
    try:
        for ric, outpath in instruments.items():
            try:
                df = download_intraday_history(
                    ric=ric,
                    outpath=outpath,
                    interval=hp.Intervals.FIVE_MINUTES,
                    lookback_days=60,
                    chunk_days=1,
                )
                print(f"\n{ric} preview:")
                print(df.head())
                print(df.tail())
                print("-" * 60)
            except Exception as e:
                print(f"Failed for {ric}: {e}")
    finally:
        ld.close_session()


if __name__ == "__main__":
    main()