-- Every active code of the Warehouse (01) and Alberdi (03) catalogs, with its category's name.
-- A branch may define one category code twice (Alberdi does), so the names are joined, not the rows.
SELECT s.COD_SUC, s.COD_PRO, s.DET_PRO, s.COD_RUB,
       (SELECT GROUP_CONCAT(DISTINCT r.DETALLE ORDER BY r.ID SEPARATOR ' / ') FROM rubros r
         WHERE r.COD_SUC = s.COD_SUC AND r.COD_RUB = s.COD_RUB AND r.ELIMINADO = 'N') AS RUBRO,
       s.PRE_CTO, s.BONIF1, s.BONIF2, s.BONIF3, s.BONIF4, s.IVA, s.UNIBUL, s.CUENTAP
  FROM stock s
 WHERE s.ELIMINADO = 'N' AND s.COD_SUC IN ('01', '03')
 ORDER BY s.COD_SUC, s.COD_PRO;
