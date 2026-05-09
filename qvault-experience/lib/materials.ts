import * as THREE from 'three';
import { PALETTE } from './MasteringPipeline';

export const COLORS = {
  void: PALETTE.deepGraphite,
  voidDeep: '#050505',
  institutionalWhite: PALETTE.institutionalWhite,
  tacticalGrey: PALETTE.coldSteel,
  steel: PALETTE.coldSteel,
  carbon: PALETTE.graphite,
  sovereignCyan: PALETTE.sovereignCyan,
  threatAmber: PALETTE.threatAmber,
  emergencyRed: PALETTE.emergencyRed,
};

export const Materials = {
  carbonAnodized: new THREE.MeshStandardMaterial({
    color: PALETTE.graphite,
    roughness: 0.88,
    metalness: 0.45,
    envMapIntensity: 0.35,
  }),

  machinedSteel: new THREE.MeshStandardMaterial({
    color: PALETTE.coldSteel,
    roughness: 0.34,
    metalness: 0.9,
    envMapIntensity: 0.75,
  }),

  darkCeramic: new THREE.MeshPhysicalMaterial({
    color: PALETTE.graphite,
    roughness: 0.42,
    metalness: 0.12,
    clearcoat: 0.45,
    clearcoatRoughness: 0.38,
    envMapIntensity: 0.45,
  }),

  emissiveInstitutional: new THREE.MeshStandardMaterial({
    color: PALETTE.institutionalWhite,
    emissive: PALETTE.sovereignCyan,
    emissiveIntensity: 0.32,
    toneMapped: true,
  }),

  emissiveDim: new THREE.MeshStandardMaterial({
    color: PALETTE.coldSteel,
    emissive: PALETTE.sovereignCyan,
    emissiveIntensity: 0.12,
    toneMapped: true,
  }),
};

export function applyEnvironmentMap(envMap: THREE.Texture) {
  Object.values(Materials).forEach((mat) => {
    if ('envMap' in mat) {
      mat.envMap = envMap;
      mat.needsUpdate = true;
    }
  });
}
