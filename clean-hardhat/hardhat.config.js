require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

module.exports = {
  solidity: {
    compilers: [
      {
        version: "0.8.20",
        settings: {
          optimizer: {
            enabled: true,
            runs: 200
          }
        }
      }
    ]
  },
  networks: {
    sepolia: {
      url: "https://rpc.sepolia.org",
      accounts: ["1e981e24e3731898790cc098d2ad8dcce2063a0898a1ce7f63a4294ae22ef2aa"],
      chainId: 11155111
    }
  }
};

