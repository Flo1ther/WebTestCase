// Translate known messages from old stored results without rewriting historical data or user text.
const messages:Record<string,string>={
 'Rule-based educational review; no external AI request was made.':'Збережена навчальна перевірка за старими правилами; зовнішнього запиту не було.',
 'Deterministic educational suggestions; review before creating real test cases.':'Збережені шаблонні пропозиції попередньої версії; перед використанням потрібен перегляд.',
 'Preconditions are empty, so the environment may be interpreted differently by testers.':'Передумови не заповнено; тестувальники можуть по-різному тлумачити середовище.',
 'State the required user role, data and system state before execution.':'Укажіть роль, дані та стан системи перед виконанням.',
 'The scenario has too few explicit steps to reproduce consistently.':'Попередня версія вважала кількість кроків недостатньою для відтворення.',
 'Split the flow into observable actions and checkpoints.':'Розділіть сценарій на спостережувані дії та контрольні результати.',
 'Add a negative or validation scenario for incorrect input.':'Стара рекомендація: додайте негативний сценарій для неправильних даних.',
 'No obvious structural gaps were detected.':'Очевидних структурних прогалин не виявлено.',
 'Keep execution evidence and expected results specific.':'Конкретизуйте очікувані результати та докази виконання.',
 'A test user is authenticated and the feature is available.':'Тестовий користувач увійшов; функціональність доступна.',
 'Perform the relevant user action':'Виконайте відповідну дію користувача',
 'Use valid data and confirm the main outcome.':'Використайте правильні дані й перевірте основний результат.',
 'Use incomplete or invalid data and verify a clear validation message.':'Використайте неповні або неправильні дані й перевірте зрозуміле повідомлення валідації.',
 'Use a boundary value and verify the system remains stable.':'Використайте граничне значення й перевірте стабільність системи.'
}
export function legacyText(value:string|undefined){if(!value)return '';return messages[value]||value.replace(/^Happy path: /,'Основний сценарій: ').replace(/^Validation: /,'Перевірка даних: ').replace(/^Boundary: /,'Граничні значення: ').replace(/^Open the feature: /,'Відкрийте функціональність: ')}
