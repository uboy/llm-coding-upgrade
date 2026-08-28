const p = (fn, userId) =>
  new Promise((resolve, reject) => fn(userId, (err, value) => (err ? reject(err) : resolve(value))));

export async function loadProfile(userId, api, done) {
  try {
    const profile = await p(api.getProfile, userId);
    const settings = await p(api.getSettings, userId);
    let avatar = null;
    try {
      avatar = await p(api.getAvatar, userId);
    } catch {
      avatar = null;
    }
    done(null, { profile, settings, avatar });
  } catch (err) {
    done(err);
  }
}
