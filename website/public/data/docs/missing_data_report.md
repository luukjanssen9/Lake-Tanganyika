# Missing Data Report

- Final dataset analyzed: `data/processed/main_modeling_table.parquet`
- Rows: 528
- Date coverage: 1981-01-01 -> 2024-12-01

## Missingness Summary per Column
| column                        |   missing_pct |   missing_count |   longest_consecutive_gap_rows |
|:------------------------------|--------------:|----------------:|-------------------------------:|
| target_value_lag_12           |          2.84 |              15 |                             12 |
| runoff_mean_lag_3             |          2.27 |              12 |                              9 |
| runoff_sum                    |          2.27 |              12 |                             12 |
| runoff_sum_lag_1              |          2.27 |              12 |                             11 |
| runoff_sum_lag_2              |          2.27 |              12 |                             10 |
| precip_mm_mean_lag_12         |          2.27 |              12 |                             12 |
| runoff_mean_lag_12            |          2.27 |              12 |                             12 |
| runoff_mean_lag_6             |          2.27 |              12 |                              6 |
| runoff_sum_lag_3              |          2.27 |              12 |                              9 |
| runoff_sum_lag_6              |          2.27 |              12 |                              6 |
| runoff_station_count          |          2.27 |              12 |                             12 |
| temp_mean_c_mean_lag_12       |          2.27 |              12 |                             12 |
| runoff_mean                   |          2.27 |              12 |                             12 |
| runoff_sum_lag_12             |          2.27 |              12 |                             12 |
| runoff_mean_lag_1             |          2.27 |              12 |                             11 |
| runoff_sum_roll_std_3         |          2.27 |              12 |                             11 |
| runoff_mean_anom              |          2.27 |              12 |                             12 |
| runoff_mean_zscore            |          2.27 |              12 |                             12 |
| runoff_mean_lag_2             |          2.27 |              12 |                             10 |
| precip_mm_sum_lag_12          |          2.27 |              12 |                             12 |
| runoff_sum_roll_mean_3        |          1.89 |              10 |                             10 |
| runoff_sum_roll_std_6         |          1.7  |               9 |                              8 |
| target_value_lag_6            |          1.7  |               9 |                              6 |
| runoff_sum_roll_mean_6        |          1.33 |               7 |                              7 |
| precip_mm_mean_lag_6          |          1.14 |               6 |                              6 |
| temp_mean_c_mean_lag_6        |          1.14 |               6 |                              6 |
| precip_mm_sum_lag_6           |          1.14 |               6 |                              6 |
| target_value_lag_3            |          1.14 |               6 |                              3 |
| target_value_lag_2            |          1.14 |               6 |                              2 |
| target_value_lag_1            |          1.14 |               6 |                              2 |
| target_value                  |          0.95 |               5 |                              2 |
| target_value_anom             |          0.95 |               5 |                              2 |
| target_value_zscore           |          0.95 |               5 |                              2 |
| target_outlier_count          |          0.95 |               5 |                              2 |
| precip_mm_sum_lag_3           |          0.57 |               3 |                              3 |
| target_value_roll_std_3       |          0.57 |               3 |                              2 |
| temp_mean_c_mean_lag_3        |          0.57 |               3 |                              3 |
| runoff_sum_roll_std_12        |          0.57 |               3 |                              2 |
| precip_mm_mean_lag_3          |          0.57 |               3 |                              3 |
| precip_mm_sum_lag_2           |          0.38 |               2 |                              2 |
| temp_mean_c_mean_lag_2        |          0.38 |               2 |                              2 |
| precip_mm_mean_lag_2          |          0.38 |               2 |                              2 |
| temp_mean_c_mean_roll_std_6   |          0.19 |               1 |                              1 |
| target_value_roll_std_12      |          0.19 |               1 |                              1 |
| target_value_roll_std_6       |          0.19 |               1 |                              1 |
| precip_mm_sum_roll_std_6      |          0.19 |               1 |                              1 |
| precip_mm_sum_lag_1           |          0.19 |               1 |                              1 |
| temp_mean_c_mean_roll_std_3   |          0.19 |               1 |                              1 |
| precip_mm_sum_roll_std_12     |          0.19 |               1 |                              1 |
| precip_mm_sum_roll_std_3      |          0.19 |               1 |                              1 |
| runoff_sum_roll_mean_12       |          0.19 |               1 |                              1 |
| precip_mm_mean_lag_1          |          0.19 |               1 |                              1 |
| temp_mean_c_mean_lag_1        |          0.19 |               1 |                              1 |
| temp_mean_c_mean_roll_std_12  |          0.19 |               1 |                              1 |
| temp_mean_c_mean_roll_mean_12 |          0    |               0 |                              0 |
| temp_mean_c_mean_anom         |          0    |               0 |                              0 |
| event_q95                     |          0    |               0 |                              0 |
| temp_mean_c_mean_zscore       |          0    |               0 |                              0 |
| precip_mm_mean_zscore         |          0    |               0 |                              0 |
| precip_mm_mean_anom           |          0    |               0 |                              0 |
| temp_mean_c_mean_roll_mean_6  |          0    |               0 |                              0 |
| date                          |          0    |               0 |                              0 |
| temp_mean_c_mean_roll_mean_3  |          0    |               0 |                              0 |
| precip_mm_sum_roll_mean_12    |          0    |               0 |                              0 |
| precip_mm_mean                |          0    |               0 |                              0 |
| precip_mm_sum                 |          0    |               0 |                              0 |
| precip_station_count          |          0    |               0 |                              0 |
| temp_mean_c_mean              |          0    |               0 |                              0 |
| temp_max_c_mean               |          0    |               0 |                              0 |
| temp_min_c_mean               |          0    |               0 |                              0 |
| temp_station_count            |          0    |               0 |                              0 |
| target_station                |          0    |               0 |                              0 |
| month                         |          0    |               0 |                              0 |
| year                          |          0    |               0 |                              0 |
| month_sin                     |          0    |               0 |                              0 |
| month_cos                     |          0    |               0 |                              0 |
| target_value_roll_mean_3      |          0    |               0 |                              0 |
| target_value_roll_mean_6      |          0    |               0 |                              0 |
| target_value_roll_mean_12     |          0    |               0 |                              0 |
| precip_mm_sum_roll_mean_3     |          0    |               0 |                              0 |
| precip_mm_sum_roll_mean_6     |          0    |               0 |                              0 |
| event_q98                     |          0    |               0 |                              0 |

## Missingness Over Time (Yearly Overall %)
|   year |   overall_missing_pct |
|-------:|----------------------:|
|   1981 |                 16.25 |
|   1982 |                  0    |
|   1983 |                  0.83 |
|   1984 |                  0.1  |
|   1985 |                  0    |
|   1986 |                  0.52 |
|   1987 |                  0.42 |
|   1988 |                  0    |
|   1989 |                  0    |
|   1990 |                  0    |
|   1991 |                  0    |
|   1992 |                  0    |
|   1993 |                  0    |
|   1994 |                  0    |
|   1995 |                  0    |
|   1996 |                  0    |
|   1997 |                  0    |
|   1998 |                  0.83 |
|   1999 |                  0.1  |
|   2000 |                  0    |
|   2001 |                  0    |
|   2002 |                  0    |
|   2003 |                  0    |
|   2004 |                  0    |
|   2005 |                  0    |
|   2006 |                  0    |
|   2007 |                  0    |
|   2008 |                  0    |
|   2009 |                  0    |
|   2010 |                  0    |
|   2011 |                  0    |
|   2012 |                  0    |
|   2013 |                  0    |
|   2014 |                  0    |
|   2015 |                  0    |
|   2016 |                  0    |
|   2017 |                  0    |
|   2018 |                  0    |
|   2019 |                  0    |
|   2020 |                  0    |
|   2021 |                  0    |
|   2022 |                  0    |
|   2023 |                  0    |
|   2024 |                 19.17 |

## Missingness Per Station
| target_station   |   overall_missing_pct |
|:-----------------|----------------------:|
| JIJI NDAGO       |                  0.87 |

## High Missingness Columns and Recommended Actions
No columns exceed 30% missingness.

## Timeline Completeness Check
- No months are missing entirely from the final monthly timeline.