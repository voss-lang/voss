export class VossApiError extends Error {
  public readonly status: number;
  public readonly detail: string;

  constructor(status: number, detail: string) {
    super(`Voss API request failed with status ${status}: ${detail}`);
    this.name = "VossApiError";
    this.status = status;
    this.detail = detail;
  }
}
