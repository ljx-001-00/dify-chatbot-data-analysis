-- ============================================================
-- 商品价格表：把「价格 / 排名 / 型号参数」从检索交给数据库
-- 用法：mysql -uroot -p wechat < products.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS products (
  model      VARCHAR(32)  NOT NULL COMMENT '型号，如 R40-A0 / JSQ30-16HM8',
  category   VARCHAR(16)  NOT NULL COMMENT '储水式 / 燃气',
  capacity_l INT          NOT NULL COMMENT '容量（升）',
  price      INT          NOT NULL COMMENT '售价（元），整数，避免小数漂移',
  energy     VARCHAR(8)   DEFAULT '' COMMENT '能效等级',
  warranty   VARCHAR(64)  DEFAULT '' COMMENT '保修政策',
  stock      INT          DEFAULT 0  COMMENT '库存',
  features   VARCHAR(255) DEFAULT '' COMMENT '一句话卖点',
  updated_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (model),
  KEY idx_price (price)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='热水器型号与价格';

-- ------------------------------------------------------------
-- 以下是【示例数据】，请用真实价目表覆盖（见 init_products.py）
-- ------------------------------------------------------------
INSERT INTO products (model, category, capacity_l, price, energy, warranty, stock, features) VALUES
('R40-A0',        '储水式', 40,  999, '一级', '内胆 8 年 / 整机 3 年', 120, '入门款，机身小巧，适合 1~2 人'),
('X50-B2',        '储水式', 50, 1499, '一级', '内胆 8 年 / 整机 3 年',  80, '双胆速热，适合 2~3 人'),
('R60-A1',        '储水式', 60, 1999, '一级', '内胆 8 年 / 整机 3 年',  60, '大容量，适合 3~4 人'),
('R60-D5',        '储水式', 60, 2599, '一级', '内胆 10 年 / 整机 5 年', 40, '变频恒温，带 WIFI 控制'),
('JSQ30-16HD9',   '燃气',   16, 3299, '一级', '整机 3 年',              35, '16 升恒温燃气，性价比款'),
('JSQ30-16HM8',   '燃气',   16, 4299, '一级', '整机 5 年',              20, '16 升零冷水，带增压')
ON DUPLICATE KEY UPDATE
  category=VALUES(category), capacity_l=VALUES(capacity_l), price=VALUES(price),
  energy=VALUES(energy), warranty=VALUES(warranty), stock=VALUES(stock),
  features=VALUES(features);
