from werkzeug.security import generate_password_hash, check_password_hash

h = generate_password_hash("test1234")
print(h)
print("---")
print(check_password_hash(h, "test1234"))  # debe imprimir True
print(check_password_hash(h, "otra"))      # debe imprimir False