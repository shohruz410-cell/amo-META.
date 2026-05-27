mig:
	flask db migrate -m "add new_field to amo_oauth"
	flask db upgrade

orqaga:
	flask db downgrade

mig_tarx:
	flask db history