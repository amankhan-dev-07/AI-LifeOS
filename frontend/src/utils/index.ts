// Performance utilities
export {
  detectDeviceCapabilities,
  getDeviceCapabilities,
  getQualitySettings,
  FRAME_BUDGET,
  isWithinFrameBudget,
  createFrameBudgetChecker,
  preloadModule,
  createLazyComponent,
} from './performance';
export type { DeviceCapabilities, QualitySettings } from './performance';