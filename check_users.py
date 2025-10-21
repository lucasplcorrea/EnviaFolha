from sqlalchemy import create_engine, text

engine = create_engine('postgresql://enviafolha_user:secure_password@localhost:5432/enviafolha_db')

with engine.connect() as conn:
    result = conn.execute(text('SELECT id, username, email FROM users ORDER BY id LIMIT 10'))
    users = result.fetchall()
    
    print('👥 Usuários no banco:')
    if users:
        for u in users:
            print(f'  ID: {u[0]}, Username: {u[1]}, Email: {u[2]}')
    else:
        print('  Nenhum usuário encontrado')
    
    conn.commit()
