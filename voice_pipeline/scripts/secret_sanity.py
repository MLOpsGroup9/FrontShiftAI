import jwt

SECRET = "a-string-secret-at-least-256-bits-long"

token ="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbkBncm91cDkuY29tIiwiY29tcGFueSI6IkZyb250U2hpZnRBSSIsInJvbGUiOiJzdXBlcl9hZG1pbiIsImV4cCI6MTc5NjYwMzc4OX0.jx2ENerr9YQArLah_rXBT8XtGBpQz846ws2ZR0mhnmI"

decoded = jwt.decode(token, SECRET, algorithms=["HS256"])
print(decoded)