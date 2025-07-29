let normalizeSlackId;

beforeAll(async () => {
  ({ normalizeSlackId } = await import('./slackUtils.js'));
});

describe('normalizeSlackId', () => {
  test('handles <@U...|alias>', () => {
    expect(normalizeSlackId('<@U12345|alias>')).toBe('U12345');
  });

  test('handles URLs', () => {
    expect(normalizeSlackId('https://example.com/team/U12345')).toBe('U12345');
  });

  test('handles team-user format', () => {
    expect(normalizeSlackId('T05NRU10WAW-U05SSCWHSV7')).toBe('U05SSCWHSV7');
  });

  test('returns empty string for falsy input', () => {
    expect(normalizeSlackId('')).toBe('');
  });
});
