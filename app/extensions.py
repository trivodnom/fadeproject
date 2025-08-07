from flask_uploads import UploadSet, IMAGES

# Создаем наш UploadSet для аватаров
avatars = UploadSet('avatars', IMAGES)