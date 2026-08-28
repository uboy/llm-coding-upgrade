export function loadProfile(userId, api, done) {
  api.getProfile(userId, (err, profile) => {
    if (err) return done(err);
    api.getSettings(userId, (err2, settings) => {
      if (err2) return done(err2);
      api.getAvatar(userId, (err3, avatar) => {
        done(null, { profile, settings, avatar: err3 ? null : avatar });
      });
    });
  });
}
