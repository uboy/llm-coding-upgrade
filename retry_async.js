async function retryAsync(fn, options) {
  const { retries, delayMs, factor = 1, shouldRetry } = options;
  const totalAttempts = Math.max(1, retries);
  let lastError;

  for (let attempt = 1; attempt <= totalAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      if (attempt === totalAttempts) {
        break;
      }
      if (shouldRetry && !shouldRetry(error, attempt)) {
        break;
      }
      const wait = delayMs * Math.pow(factor, attempt - 1);
      await new Promise((resolve) => setTimeout(resolve, wait));
    }
  }

  throw lastError;
}

module.exports = { retryAsync };
