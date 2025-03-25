module.exports = {
  networks: {
    ganacheCLI: {
      host: "127.0.0.1",
      port: 8545,
      network_id: "*",
    },
    ganacheDesktop: {
      host: "127.0.0.1",
      port: 7545, // Default Ganache Desktop port
      network_id: "*",
    }
  },
  compilers: {
    solc: {
      version: "0.8.20"
    }
  }
};
  

/*
The configuration file is pretty straightforward. It defines two networks,  ganacheCLI  and  ganacheDesktop , which connect to the local Ganache CLI and Ganache Desktop instances, respectively. 
  The  compilers  section specifies the Solidity compiler version to use. 
  4. Deploy the Smart Contract 
  Now that we have our smart contract and configuration file in place, we can deploy the contract to the blockchain. 
  To deploy the contract, run the following command: 
  $ truffle migrate --network ganacheCLI
  
  The command tells Truffle to deploy the contract to the Ganache CLI network. 
  If the deployment is successful, you should see output similar to the following: 
  Compiling your contracts...
*/