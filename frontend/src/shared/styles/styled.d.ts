import "styled-components";
import type { AppTheme } from "./theme";

declare module "styled-components" {
  export interface DefaultTheme {
    color: AppTheme["color"];
    radius: AppTheme["radius"];
    shadow: AppTheme["shadow"];
    layout: AppTheme["layout"];
  }
}
