# GITART
## Описание
GitArt - это клиент нотификатор реализованый на python. Программа размещается в системном трее и содержит 2 пункта меню.
* Настройки
  * При нажатие показывает окно настроек позволяющие ввести токен - для авторизации, адрес сервера и интервал получение новых сообщений.
* Завершить программу
  * При нажатие завершает программу.
  
После авторизации приложение в фоновом режиме проверяет наличие непроверенных сообщений и оповещает о них - с помощью анимации, меняющие аватар пользователя на почтовый ящик и обратно. При нажатие левой кнопкой мыши на трей, если есть непрочитанные сообщения, открывается окно содержащая 2 окна.
* Непрочитанные сообщения.
  * В окне "непрочитанные сообщения" содержаться все сообщения, которые вы не открывали с такой информацией как: время создание,кем создано, комментарий и тому подобное c возможностью, открыть это сообщений в браузере.
* Назначенно вам.
  * В окне "назначенно вам", содержаться назначенные вам задачи с возможностью открыть их в браузере.
## Как авторизироваться
Для авторизации нужно получить токен вашей учетной записи и сохранить его в настройках.