/**
 * 3D Scene and USD Type Definitions
 */

export interface USDPrimitive {
  type: 'Sphere' | 'Cube' | 'Cylinder' | 'Mesh' | 'Cone';
  name: string;
  path: string;
  transform?: {
    translate?: [number, number, number];
    scale?: [number, number, number];
    rotate?: [number, number, number];
  };
  material?: {
    color?: [number, number, number];
    metallic?: number;
    roughness?: number;
    opacity?: number;
  };
  geometry?: {
    radius?: number;                  // Sphere, Cylinder, Cone
    height?: number;                  // Cylinder, Cone
    size?: [number, number, number];  // Cube
  };
}

export interface ParsedScene {
  primitives: USDPrimitive[];
  metadata?: {
    upAxis?: 'Y' | 'Z';
    metersPerUnit?: number;
  };
}

export interface SceneObject {
  id: string;
  name: string;
  type: string;
  meshId?: string;
  visible: boolean;
}
