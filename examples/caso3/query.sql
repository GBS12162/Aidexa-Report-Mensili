WITH query_principale_500 AS (
  SELECT
    tabella_principale.mydate,
    tabella_principale.sl_url,
    tabella_principale.stato,
    COUNT(tabella_principale.sl_guid) AS conteggio
  FROM (
    SELECT
      TRUNC(logs.sl_ins_time) AS mydate,
      p.prodcode,
      p.co_id,
      logs.sl_guid,
      p.stato,
      logs.sl_step_number,
      logs.sl_url,
      COUNT(*) AS conteggio
    FROM onb_lg_service_log logs
    JOIN onb_tr_process p
      ON logs.sl_guid = p.guid
    JOIN onb_tr_onboarding_prdt pr
      ON pr.id = p.prodid
    WHERE pr.abi = '03625'
      AND pr.prdt_code IN ('DEPOSITO_VINCOLATO_AIDEXA')
      --, 'DEPOSITO_LIBERO_AIDEXA')
      AND logs.sl_status_code = '500'
      AND logs.sl_component = 'WGT'
      AND logs.sl_ser_type = 'RES'
      AND sl_ins_time >= TO_TIMESTAMP(
        '01/08/2025 00:00:00.000000',
        'DD/MM/YYYY HH24:MI:SS.FF6'
      )
      AND sl_ins_time < TO_TIMESTAMP(
        '31/08/2025 23:59:59.999999',
        'DD/MM/YYYY HH24:MI:SS.FF6'
      )
    GROUP BY
      TRUNC(logs.sl_ins_time),
      p.prodcode,
      p.co_id,
      logs.sl_guid,
      p.stato,
      logs.sl_step_number,
      logs.sl_url
    ORDER BY 1 ASC, 2 DESC
  ) tabella_principale
  GROUP BY
    tabella_principale.mydate,
    tabella_principale.sl_url,
    tabella_principale.stato
),
query_principale_400 AS (
  SELECT
    tabella_principale1.mydate,
    tabella_principale1.sl_url,
    tabella_principale1.stato,
    COUNT(tabella_principale1.sl_guid) AS conteggio
  FROM (
    SELECT
      TRUNC(logs.sl_ins_time) AS mydate,
      p.prodcode,
      p.co_id,
      logs.sl_guid,
      p.stato,
      logs.sl_step_number,
      logs.sl_url,
      COUNT(*) AS conteggio
    FROM onb_lg_service_log logs
    JOIN onb_tr_process p
      ON logs.sl_guid = p.guid
    JOIN onb_tr_onboarding_prdt pr
      ON pr.id = p.prodid
    WHERE pr.abi = '03625'
      AND pr.prdt_code IN ('DEPOSITO_VINCOLATO_AIDEXA')
      --, 'DEPOSITO_LIBERO_AIDEXA')
      AND logs.sl_status_code = '400'
      AND logs.sl_component = 'WGT'
      AND logs.sl_ser_type = 'RES'
      AND sl_ins_time >= TO_TIMESTAMP(
        '01/08/2025 00:00:00.000000',
        'DD/MM/YYYY HH24:MI:SS.FF6'
      )
      AND sl_ins_time < TO_TIMESTAMP(
        '31/08/2025 23:59:59.999999',
        'DD/MM/YYYY HH24:MI:SS.FF6'
      )
    GROUP BY
      TRUNC(logs.sl_ins_time),
      p.prodcode,
      p.co_id,
      logs.sl_guid,
      p.stato,
      logs.sl_step_number,
      logs.sl_url
    ORDER BY 1 ASC, 2 DESC
  ) tabella_principale1
  GROUP BY
    tabella_principale1.mydate,
    tabella_principale1.sl_url,
    tabella_principale1.stato
),
urls_500 AS (
  SELECT DISTINCT sl_url
  FROM query_principale_500
),
stati_totali AS (
  SELECT stato
  FROM (
    SELECT 'A' AS stato FROM dual
    UNION
    SELECT 'D' AS stato FROM dual
    UNION
    SELECT 'F' AS stato FROM dual
    UNION
    SELECT 'I' AS stato FROM dual
    UNION
    SELECT 'K' AS stato FROM dual
    UNION
    SELECT 'N' AS stato FROM dual
    UNION
    SELECT 'P' AS stato FROM dual
    UNION
    SELECT 'T' AS stato FROM dual
  )
),
urls_400 AS (
  SELECT DISTINCT sl_url
  FROM query_principale_400
),
completo_500 AS (
  SELECT
    a.mydate AS dataa,
    urls_500.sl_url AS urll,
    stati_totali.stato AS statoo
  FROM query_principale_500 a,
     urls_500,
     stati_totali
),
completo_400 AS (
  SELECT
    a.mydate AS dataa,
    urls_400.sl_url AS urll,
    stati_totali.stato AS statoo
  FROM query_principale_400 a,
     urls_400,
     stati_totali
)
SELECT *
FROM (
  SELECT DISTINCT
    a.urll,
    a.dataa,
    a.statoo,
    '500' AS tipo_errore,
    NVL(t2.conteggio, 0),
    t2.conteggio
  FROM completo_500 a
  FULL OUTER JOIN query_principale_500 t2
    ON a.dataa = t2.mydate
    AND a.statoo = t2.stato
    AND a.urll = t2.sl_url

  UNION

  SELECT DISTINCT
    a.urll,
    a.dataa,
    a.statoo,
    '400' AS tipo_errore,
    NVL(t2.conteggio, 0),
    t2.conteggio
  FROM completo_400 a
  FULL OUTER JOIN query_principale_400 t2
    ON a.dataa = t2.mydate
    AND a.statoo = t2.stato
    AND a.urll = t2.sl_url
)
ORDER BY 2, 1, 3 ASC;