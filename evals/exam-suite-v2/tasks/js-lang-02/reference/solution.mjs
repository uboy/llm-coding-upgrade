export function paginate(fetchPage) {
  return {
    [Symbol.asyncIterator]() {
      let buffer = [];
      let cursor = null;
      let started = false;
      let done = false;
      return {
        async next() {
          if (done) return { value: undefined, done: true };
          while (buffer.length === 0) {
            if (started && cursor === null) {
              done = true;
              return { value: undefined, done: true };
            }
            const page = await fetchPage(cursor);
            started = true;
            buffer = [...page.items];
            cursor = page.nextCursor;
          }
          return { value: buffer.shift(), done: false };
        },
      };
    },
  };
}
