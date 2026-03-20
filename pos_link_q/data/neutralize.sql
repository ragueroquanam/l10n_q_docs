UPDATE pos_payment_provider AS ppp
SET
    base_url = 'https://poslink.hm.opos.com.uy',
    active = FALSE
WHERE code = 'poslink';
