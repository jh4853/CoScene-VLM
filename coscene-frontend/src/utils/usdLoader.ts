/**
 * USD Loader utility using Three.js USDZLoader
 */

import * as THREE from 'three';

/**
 * Load USD from text content (USDA format)
 * Since Three.js USDZLoader expects binary USDZ, we'll parse text USD manually
 * This is a simplified parser for basic primitives
 */
export async function loadUSDFromText(usdContent: string): Promise<THREE.Group> {
  const group = new THREE.Group();
  group.name = 'Scene';

  // Simple text-based parsing for common primitives
  const primitives = parseUSDText(usdContent);

  primitives.forEach((prim) => {
    const mesh = createMeshFromPrimitive(prim);
    if (mesh) {
      group.add(mesh);
    }
  });

  return group;
}

/**
 * Simple USD text parser for basic primitives
 */
interface USDPrimitive {
  type: string;
  name: string;
  transform?: {
    translate?: [number, number, number];
    scale?: [number, number, number];
  };
  material?: {
    color?: [number, number, number];
  };
  geometry?: {
    radius?: number;
    height?: number;
    size?: [number, number, number];
  };
}

function parseUSDText(usdContent: string): USDPrimitive[] {
  const primitives: USDPrimitive[] = [];
  const materials: Map<string, [number, number, number]> = new Map();
  const lines = usdContent.split('\n');

  // First pass: parse materials
  let inMaterialScope = false;
  let currentMaterialPath = '';
  let currentMaterialColor: [number, number, number] | null = null;

  for (const line of lines) {
    const trimmed = line.trim();

    // Check if we're in a Material definition
    const materialMatch = trimmed.match(/def\s+Material\s+"([^"]+)"/);
    if (materialMatch) {
      inMaterialScope = true;
      currentMaterialPath = materialMatch[1];
      currentMaterialColor = null;
      continue;
    }

    // Parse diffuseColor in material scope
    if (inMaterialScope && trimmed.includes('diffuseColor')) {
      const vec = extractVector3(trimmed);
      if (vec) {
        currentMaterialColor = vec;
      }
    }

    // End of material definition
    if (inMaterialScope && trimmed === '}') {
      if (currentMaterialColor) {
        materials.set(currentMaterialPath, currentMaterialColor);
      }
      inMaterialScope = false;
    }
  }

  // Second pass: parse primitives
  let currentPrim: Partial<USDPrimitive> | null = null;
  let materialBinding: string | null = null;

  for (const line of lines) {
    const trimmed = line.trim();

    // Match def statements
    const defMatch = trimmed.match(/def\s+(Sphere|Cube|Cylinder|Cone)\s+"([^"]+)"/);
    if (defMatch) {
      if (currentPrim?.type && currentPrim?.name) {
        // Apply material binding if found
        if (materialBinding) {
          const materialName = materialBinding.split('/').pop();
          if (materialName && materials.has(materialName)) {
            currentPrim.material = { color: materials.get(materialName) };
          }
        }
        primitives.push(currentPrim as USDPrimitive);
        materialBinding = null;
      }
      currentPrim = {
        type: defMatch[1],
        name: defMatch[2],
        transform: {},
        material: {},
        geometry: {},
      };
      continue;
    }

    if (!currentPrim) continue;

    // Parse material binding
    if (trimmed.includes('material:binding')) {
      const bindingMatch = trimmed.match(/<([^>]+)>/);
      if (bindingMatch) {
        materialBinding = bindingMatch[1];
      }
    }

    // Parse translate
    if (trimmed.includes('xformOp:translate')) {
      const vec = extractVector3(trimmed);
      if (vec && currentPrim.transform) currentPrim.transform.translate = vec;
    }

    // Parse scale
    if (trimmed.includes('xformOp:scale')) {
      const vec = extractVector3(trimmed);
      if (vec && currentPrim.transform) currentPrim.transform.scale = vec;
    }

    // Parse inline color (if present)
    if (trimmed.includes('diffuseColor')) {
      const vec = extractVector3(trimmed);
      if (vec && currentPrim.material) currentPrim.material.color = vec;
    }

    // Parse radius
    if (trimmed.includes('radius')) {
      const val = extractFloat(trimmed);
      if (val !== null && currentPrim.geometry) currentPrim.geometry.radius = val;
    }

    // Parse height
    if (trimmed.includes('height')) {
      const val = extractFloat(trimmed);
      if (val !== null && currentPrim.geometry) currentPrim.geometry.height = val;
    }

    // End of definition
    if (trimmed === '}' && currentPrim.type && currentPrim.name) {
      // Apply material binding if found
      if (materialBinding) {
        const materialName = materialBinding.split('/').pop();
        if (materialName && materials.has(materialName)) {
          currentPrim.material = { color: materials.get(materialName) };
        }
      }
      primitives.push(currentPrim as USDPrimitive);
      currentPrim = null;
      materialBinding = null;
    }
  }

  return primitives;
}

function extractVector3(line: string): [number, number, number] | null {
  const match = line.match(/\(([^)]+)\)/);
  if (!match) return null;
  const values = match[1].split(',').map((v) => parseFloat(v.trim()));
  return values.length === 3 ? [values[0], values[1], values[2]] : null;
}

function extractFloat(line: string): number | null {
  const match = line.match(/=\s*([\d.]+)/);
  return match ? parseFloat(match[1]) : null;
}

/**
 * Create Three.js mesh from parsed primitive
 */
function createMeshFromPrimitive(prim: USDPrimitive): THREE.Mesh | null {
  let geometry: THREE.BufferGeometry | null = null;

  // Create geometry based on type
  switch (prim.type) {
    case 'Sphere':
      geometry = new THREE.SphereGeometry(prim.geometry?.radius || 1, 32, 32);
      break;
    case 'Cube':
      const size = prim.geometry?.size || [1, 1, 1];
      geometry = new THREE.BoxGeometry(size[0], size[1], size[2]);
      break;
    case 'Cylinder':
      geometry = new THREE.CylinderGeometry(
        prim.geometry?.radius || 0.5,
        prim.geometry?.radius || 0.5,
        prim.geometry?.height || 1,
        32
      );
      break;
    case 'Cone':
      geometry = new THREE.ConeGeometry(
        prim.geometry?.radius || 0.5,
        prim.geometry?.height || 1,
        32
      );
      break;
    default:
      return null;
  }

  // Create material
  const color = prim.material?.color || [0.5, 0.5, 0.5];
  const material = new THREE.MeshStandardMaterial({
    color: new THREE.Color(color[0], color[1], color[2]),
  });

  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = prim.name;

  // Apply transforms
  if (prim.transform?.translate) {
    mesh.position.set(...prim.transform.translate);
  }
  if (prim.transform?.scale) {
    mesh.scale.set(...prim.transform.scale);
  }

  return mesh;
}
