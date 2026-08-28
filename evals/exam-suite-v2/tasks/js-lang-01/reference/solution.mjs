export function makeAudited(target, onChange) {
  return new Proxy(target, {
    set(obj, key, value) {
      const old = obj[key];
      if (old !== value) {
        obj[key] = value;
        onChange(key, old, value);
      }
      return true;
    },
    deleteProperty(obj, key) {
      if (key in obj) {
        const old = obj[key];
        delete obj[key];
        onChange(key, old, undefined);
      }
      return true;
    },
  });
}
