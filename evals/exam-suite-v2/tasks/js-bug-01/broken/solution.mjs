export function makeTotaler() {
  return {
    sum: 0,
    add(kopecks) {
      this.sum += kopecks;
    },
    get total() {
      return this.sum;
    },
  };
}
