-- Every active code of the Warehouse (01) and Alberdi (03) catalogs, with its category's name.
-- A branch may define one category code twice (Alberdi does), so the names are joined, not the rows.
-- LIVE: the code shows activity in this backup (Alberdi has no sales in it): a stock row in its own
-- branch, a price raised in 2025 or later, or a change to the code in 2026.
SELECT s.COD_SUC, s.COD_PRO, s.DET_PRO, s.COD_RUB,
       (SELECT GROUP_CONCAT(DISTINCT r.DETALLE ORDER BY r.ID SEPARATOR ' / ') FROM rubros r
         WHERE r.COD_SUC = s.COD_SUC AND r.COD_RUB = s.COD_RUB AND r.ELIMINADO = 'N') AS RUBRO,
       s.PRE_CTO, s.BONIF1, s.BONIF2, s.BONIF3, s.BONIF4, s.IVA, s.UNIBUL, s.CUENTAP,
       (ss.COD_PRO IS NOT NULL OR IFNULL(YEAR(s.FEC_ULT_AUM) >= 2025, 0) OR IFNULL(YEAR(s.ACT_FECH) >= 2026, 0)) AS LIVE,
       s.FEC_ULT_AUM, DATE(s.ACT_FECH) AS ACT_FECH
  FROM stock s
  -- stock and stock_suc have no indexes: one pass over a derived table, not a subquery per row.
  LEFT JOIN (SELECT DISTINCT COD_SUC, COD_PRO FROM stock_suc) ss
         ON ss.COD_SUC = s.COD_SUC AND ss.COD_PRO = s.COD_PRO
 WHERE s.ELIMINADO = 'N' AND s.COD_SUC IN ('01', '03')
 ORDER BY s.COD_SUC, s.COD_PRO;
