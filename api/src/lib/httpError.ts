// Throw this anywhere in a route; the central error handler turns it into a JSON response.
export class HttpError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
