СТУДЕНТА ТРЕТЬЕГО КУРСА

ПРОГРАММЫ **"ИНФОРМАТИКА"**

ПОСТОЯННОЙ ФОРМЫ ОБУЧЕНИЯ

Marchan Yan (Марчан Ян)

e-mail: <marchan.yan@student.ehu.lt>

Директору филиала ЕГУ

"Школа цифрового инжиниринга EPAM"

**ЗАЯВЛЕНИЕ**

**О ТЕМЕ ДИПЛОМНОГО ПРОЕКТА**

2025.07.06

Прошу утвердить следующую тему и критерии сложности в качестве дипломного проекта:

Тема «Интеллектуальная система агрегации данных с веб-ресурсов на основе обработки естественного языка с использованием больших языковых моделей»

Краткое описание: «Данный дипломный проект направлен на разработку интеллектуальной системы агрегации данных с веб-страниц с использованием больших языковых моделей (LLM). Система обрабатывает текстовые запросы пользователя на естественном языке и с помощью LLM автоматически формирует шаблоны извлечения информации. Использование LLM позволяет адаптивно анализировать структуру страниц и значительно снизить зависимость от ручного программирования»

Topic: "Intelligent system for aggregating data from web resources based on natural language processing using large language models"

Short description: "This thesis project focuses on the development of an intelligent data aggregation system for web pages, powered by large language models (LLMs). The system interprets user queries in natural language and uses LLMs to automatically generate data extraction patterns. Leveraging LLMs enables adaptive analysis of page structures and significantly reduces the need for manual intervention"

Критерии сложности и составные компоненты проекта (не менее одного критерия в каждой категории):

|     | **Критерий** | **Описание** |
| --- | --- | --- |
| 1   | Back-end | FastAPI-сервис для обработки запросов, генерации регулярных выражений и управления задачами скрейпинга. |
| 2   | AI assistant / Chatbot | Использование LLM для интерпретации пользовательского запроса на естественном языке и генерации регулярных выражений. |
| 3   | Database | PostgreSQL для хранения HTML, регулярных выражений, истории запросов и расписаний. |
| 4   | Microservices | Архитектура разделена на микросервисы: API, RegEx-генерация, планировщик, headless-обработчик. |
| 5   | Automated tests ≥ 70% coverage | Тестирование бизнес-логики и API с покрытием не менее 70% с использованием Pytest. |
| 6   | Containerization | Каждый сервис обёрнут в Docker-контейнер, используется Docker Compose для оркестрации. |
| 7   | API documentation | Автоматическая генерация документации через OpenAPI/Swagger на базе FastAPI. |

Руководитель дипломного проекта - Третьяк Евгений

Место работы руководителя дипломного проекта - UAB EPAM Sistemos

Должность руководителя дипломного проекта - Lead Software Engineer

Образование руководителя дипломного проекта - Belarus State Economic University, Faculty of Economics and Management, Specialist