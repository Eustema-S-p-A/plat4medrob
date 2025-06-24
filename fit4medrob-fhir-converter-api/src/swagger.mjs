import swaggerJsdoc from 'swagger-jsdoc';

const options = {
  definition: {
    openapi: "3.1.0",
    info: {
      title: "Nodejs Express API with Swagger",
      version: "0.1.0",
      description:
        "This is a simple CRUD API application made with Express and documented with Swagger",
    },
    servers: [
      {
        url: "http://localhost:4000",
      },
    ],
  },
  apis: ["./src/api/routes.mjs"],
};

const openapiSpecification = swaggerJsdoc(options);

export default openapiSpecification;