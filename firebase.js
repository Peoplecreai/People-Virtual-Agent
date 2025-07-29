import admin from 'firebase-admin';
import { SecretManagerServiceClient } from '@google-cloud/secret-manager';

const PROJECT_ID = 'people-virtual-agent-403056684625';
const SECRET_NAME = `projects/${PROJECT_ID}/secrets/MY_GOOGLE_CREDS/versions/latest`;

const secretClient = new SecretManagerServiceClient();

async function getServiceAccountJson() {
  const [version] = await secretClient.accessSecretVersion({ name: SECRET_NAME });
  const payload = version.payload.data.toString('utf8');
  return JSON.parse(payload);
}

// Solo inicializa una vez
let initializing = null;
export const getDb = async () => {
  if (admin.apps.length) return admin.firestore();
  if (!initializing) {
    initializing = getServiceAccountJson().then((serviceAccount) => {
      admin.initializeApp({ credential: admin.credential.cert(serviceAccount) });
      return admin.firestore();
    });
  }
  return initializing;
};
