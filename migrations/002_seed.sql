INSERT INTO groups (id, name) VALUES (1, 'Goa Trip') ON CONFLICT DO NOTHING;
SELECT setval('groups_id_seq', GREATEST((SELECT MAX(id) FROM groups),1));
INSERT INTO members (group_id, name) VALUES (1,'Asha'),(1,'Vikram'),(1,'Priya')
ON CONFLICT DO NOTHING;

-- 1000 rupees between 3 -> 33334 + 33333 + 33333 paise, which is the
-- rounding case the brief asks about
INSERT INTO bills (group_id, payer_id, amount_paise, note)
SELECT 1, (SELECT id FROM members WHERE name='Asha'), 100000, 'Hotel'
WHERE NOT EXISTS (SELECT 1 FROM bills);
INSERT INTO shares (bill_id, member_id, paise)
SELECT b.id, m.id,
       CASE WHEN row_number() OVER (ORDER BY m.id) = 1 THEN 33334 ELSE 33333 END
FROM bills b, members m WHERE b.note='Hotel' AND m.group_id=1
ON CONFLICT DO NOTHING;
