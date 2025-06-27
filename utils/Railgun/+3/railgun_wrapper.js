const { RailgunEngine } = require('@railgun-community/engine');
const { NetworkName, EVMGasType, getEVMGasTypeForTransaction } = require('@railgun-community/shared-models');
const {
  gasEstimateForShield,
  gasEstimateForUnshield,
  gasEstimateForTransfer,
  populateShield,
  populateUnshield,
  populateTransfer,
  getShieldPrivateKeySignatureMessage,
  createRailgunWallet,
  loadExistingWallet,
  getWalletTransactionHistory,
  getERC20AndNFTBalances,
  refreshBalances
} = require('@railgun-community/wallet');
const { ethers } = require('ethers');
const fs = require('fs');
const path = require('path');

class RailgunJSWrapper {
  constructor() {
    this.railgunEngine = null;
    this.wallet = null;
    this.provider = null;
    this.signer = null;
    this.network = null;
    this.isInitialized = false;
  }

  async initialize(network = 'polygon', rpcUrl = null, privateKey = null) {
    try {
      this.network = network;

      const networkName = this.getNetworkName(network);
      const defaultRpcUrl = this.getDefaultRpcUrl(network);

      this.provider = new ethers.JsonRpcProvider(rpcUrl || defaultRpcUrl);

      if (privateKey) {
        this.signer = new ethers.Wallet(privateKey, this.provider);
      }

      this.railgunEngine = await RailgunEngine.initForWallet(
        'RailgunWrapper',
        this.getStoragePath(),
        true,
        undefined,
        undefined,
        undefined,
        true
      );

      await this.railgunEngine.loadNetwork(
        networkName,
        this.provider,
        0,
        undefined,
        undefined,
        0
      );

      this.isInitialized = true;
      console.log(`Railgun engine initialized for ${network}`);

      return {
        success: true,
        message: `Initialized on ${network}`,
        blockNumber: await this.provider.getBlockNumber()
      };
    } catch (error) {
      console.error('Initialization failed:', error);
      return { success: false, error: error.message };
    }
  }

  async createWallet(mnemonic = null, password = 'defaultPassword') {
    try {
      if (!this.isInitialized) {
        throw new Error('Engine not initialized');
      }

      let walletMnemonic;
      if (mnemonic) {
        walletMnemonic = mnemonic;
      } else {
        walletMnemonic = ethers.Mnemonic.entropyToPhrase(ethers.randomBytes(16));
      }

      const wallet = await createRailgunWallet(
        password,
        walletMnemonic,
        0,
        false
      );

      this.wallet = wallet;

      return {
        success: true,
        wallet: {
          id: wallet.id,
          address: wallet.address,
          mnemonic: walletMnemonic
        }
      };
    } catch (error) {
      console.error('Wallet creation failed:', error);
      return { success: false, error: error.message };
    }
  }

  async loadWallet(mnemonic, password = 'defaultPassword') {
    try {
      if (!this.isInitialized) {
        throw new Error('Engine not initialized');
      }

      const wallet = await loadExistingWallet(
        password,
        mnemonic,
        0,
        false
      );

      this.wallet = wallet;

      return {
        success: true,
        wallet: {
          id: wallet.id,
          address: wallet.address
        }
      };
    } catch (error) {
      console.error('Wallet loading failed:', error);
      return { success: false, error: error.message };
    }
  }

  async getBalances() {
    try {
      if (!this.wallet) {
        throw new Error('No wallet loaded');
      }

      await refreshBalances(
        this.getNetworkName(this.network),
        this.wallet.id
      );

      const balances = await getERC20AndNFTBalances(
        this.getNetworkName(this.network),
        this.wallet.id
      );

      return {
        success: true,
        balances: balances
      };
    } catch (error) {
      console.error('Failed to get balances:', error);
      return { success: false, error: error.message };
    }
  }

  async shieldTokens(tokenAddress, amount, gasPrice = null) {
    try {
      if (!this.wallet || !this.signer) {
        throw new Error('Wallet and signer required');
      }

      const networkName = this.getNetworkName(this.network);

      const shieldPrivateKey = ethers.keccak256(
        await this.signer.signMessage(getShieldPrivateKeySignatureMessage())
      );

      const erc20AmountRecipients = [{
        tokenAddress: tokenAddress,
        amount: BigInt(amount),
        recipientAddress: this.wallet.address
      }];

      const nftAmountRecipients = [];

      const gasEstimate = await gasEstimateForShield(
        networkName,
        shieldPrivateKey,
        erc20AmountRecipients,
        nftAmountRecipients
      );

      const sendWithPublicWallet = true;
      const evmGasType = getEVMGasTypeForTransaction(networkName, sendWithPublicWallet);

      let gasDetails;
      switch (evmGasType) {
        case EVMGasType.Type0:
        case EVMGasType.Type1:
          gasDetails = {
            evmGasType,
            gasEstimate: gasEstimate.gasEstimate,
            gasPrice: BigInt(gasPrice || await this.provider.getGasPrice())
          };
          break;
        case EVMGasType.Type2:
          const feeData = await this.provider.getFeeData();
          gasDetails = {
            evmGasType,
            gasEstimate: gasEstimate.gasEstimate,
            maxFeePerGas: feeData.maxFeePerGas,
            maxPriorityFeePerGas: feeData.maxPriorityFeePerGas
          };
          break;
      }

      const { transaction } = await populateShield(
        networkName,
        shieldPrivateKey,
        erc20AmountRecipients,
        nftAmountRecipients,
        gasDetails
      );

      const txResponse = await this.signer.sendTransaction(transaction);
      const receipt = await txResponse.wait();

      return {
        success: true,
        txHash: receipt.hash,
        status: receipt.status === 1 ? 'confirmed' : 'failed',
        gasUsed: receipt.gasUsed.toString(),
        blockNumber: receipt.blockNumber
      };
    } catch (error) {
      console.error('Shield failed:', error);
      return { success: false, error: error.message };
    }
  }

  async unshieldTokens(tokenAddress, amount, recipientAddress, gasPrice = null) {
    try {
      if (!this.wallet || !this.signer) {
        throw new Error('Wallet and signer required');
      }

      const networkName = this.getNetworkName(this.network);

      const erc20AmountRecipients = [{
        tokenAddress: tokenAddress,
        amount: BigInt(amount),
        recipientAddress: recipientAddress
      }];

      const nftAmountRecipients = [];

      const gasEstimate = await gasEstimateForUnshield(
        networkName,
        this.wallet.id,
        erc20AmountRecipients,
        nftAmountRecipients
      );

      const sendWithPublicWallet = false;
      const evmGasType = getEVMGasTypeForTransaction(networkName, sendWithPublicWallet);

      let gasDetails;
      switch (evmGasType) {
        case EVMGasType.Type0:
        case EVMGasType.Type1:
          gasDetails = {
            evmGasType,
            gasEstimate: gasEstimate.gasEstimate,
            gasPrice: BigInt(gasPrice || await this.provider.getGasPrice())
          };
          break;
        case EVMGasType.Type2:
          const feeData = await this.provider.getFeeData();
          gasDetails = {
            evmGasType,
            gasEstimate: gasEstimate.gasEstimate,
            maxFeePerGas: feeData.maxFeePerGas,
            maxPriorityFeePerGas: feeData.maxPriorityFeePerGas
          };
          break;
      }

      const { transaction } = await populateUnshield(
        networkName,
        this.wallet.id,
        erc20AmountRecipients,
        nftAmountRecipients,
        gasDetails,
        true
      );

      const txResponse = await this.signer.sendTransaction(transaction);
      const receipt = await txResponse.wait();

      return {
        success: true,
        txHash: receipt.hash,
        status: receipt.status === 1 ? 'confirmed' : 'failed',
        gasUsed: receipt.gasUsed.toString(),
        blockNumber: receipt.blockNumber
      };
    } catch (error) {
      console.error('Unshield failed:', error);
      return { success: false, error: error.message };
    }
  }

  async privateTransfer(tokenAddress, amount, recipientRailgunAddress, gasPrice = null) {
    try {
      if (!this.wallet || !this.signer) {
        throw new Error('Wallet and signer required');
      }

      const networkName = this.getNetworkName(this.network);

      const erc20AmountRecipients = [{
        tokenAddress: tokenAddress,
        amount: BigInt(amount),
        recipientAddress: recipientRailgunAddress
      }];

      const nftAmountRecipients = [];

      const gasEstimate = await gasEstimateForTransfer(
        networkName,
        this.wallet.id,
        erc20AmountRecipients,
        nftAmountRecipients
      );

      const sendWithPublicWallet = false;
      const evmGasType = getEVMGasTypeForTransaction(networkName, sendWithPublicWallet);

      let gasDetails;
      switch (evmGasType) {
        case EVMGasType.Type0:
        case EVMGasType.Type1:
          gasDetails = {
            evmGasType,
            gasEstimate: gasEstimate.gasEstimate,
            gasPrice: BigInt(gasPrice || await this.provider.getGasPrice())
          };
          break;
        case EVMGasType.Type2:
          const feeData = await this.provider.getFeeData();
          gasDetails = {
            evmGasType,
            gasEstimate: gasEstimate.gasEstimate,
            maxFeePerGas: feeData.maxFeePerGas,
            maxPriorityFeePerGas: feeData.maxPriorityFeePerGas
          };
          break;
      }

      const { transaction } = await populateTransfer(
        networkName,
        this.wallet.id,
        erc20AmountRecipients,
        nftAmountRecipients,
        gasDetails,
        true
      );

      const txResponse = await this.signer.sendTransaction(transaction);
      const receipt = await txResponse.wait();

      return {
        success: true,
        txHash: receipt.hash,
        status: receipt.status === 1 ? 'confirmed' : 'failed',
        gasUsed: receipt.gasUsed.toString(),
        blockNumber: receipt.blockNumber
      };
    } catch (error) {
      console.error('Private transfer failed:', error);
      return { success: false, error: error.message };
    }
  }

  async getTransactionHistory() {
    try {
      if (!this.wallet) {
        throw new Error('No wallet loaded');
      }

      const history = await getWalletTransactionHistory(
        this.getNetworkName(this.network),
        this.wallet.id,
        0,
        50
      );

      return {
        success: true,
        transactions: history
      };
    } catch (error) {
      console.error('Failed to get transaction history:', error);
      return { success: false, error: error.message };
    }
  }

  async scanNetwork() {
    try {
      if (!this.isInitialized) {
        throw new Error('Engine not initialized');
      }

      await this.railgunEngine.scanContractHistory(
        this.getNetworkName(this.network),
        undefined,
        undefined
      );

      return { success: true, message: 'Network scan completed' };
    } catch (error) {
      console.error('Network scan failed:', error);
      return { success: false, error: error.message };
    }
  }

  getNetworkName(network) {
    const networkMap = {
      'ethereum': NetworkName.Ethereum,
      'polygon': NetworkName.Polygon,
      'bsc': NetworkName.BNBChain,
      'arbitrum': NetworkName.Arbitrum
    };
    return networkMap[network] || NetworkName.Polygon;
  }

  getDefaultRpcUrl(network) {
    const rpcUrls = {
      'ethereum': 'https://eth-mainnet.g.alchemy.com/v2/demo',
      'polygon': 'https://polygon-mainnet.g.alchemy.com/v2/demo',
      'bsc': 'https://bsc-dataseed.binance.org/',
      'arbitrum': 'https://arb1.arbitrum.io/rpc'
    };
    return rpcUrls[network] || rpcUrls['polygon'];
  }

  getStoragePath() {
    const homeDir = require('os').homedir();
    const railgunDir = path.join(homeDir, '.railgun-js');

    if (!fs.existsSync(railgunDir)) {
      fs.mkdirSync(railgunDir, { recursive: true });
    }

    return railgunDir;
  }

  async cleanup() {
    try {
      if (this.railgunEngine) {
        await this.railgunEngine.unload();
      }
      return { success: true, message: 'Cleanup completed' };
    } catch (error) {
      console.error('Cleanup failed:', error);
      return { success: false, error: error.message };
    }
  }
}

module.exports = { RailgunJSWrapper };

if (require.main === module) {
  const wrapper = new RailgunJSWrapper();

  const args = process.argv.slice(2);
  const command = args[0];

  async function handleCommand() {
    try {
      switch (command) {
        case 'init':
          const network = args[1] || 'polygon';
          const rpcUrl = args[2];
          const privateKey = args[3];
          const result = await wrapper.initialize(network, rpcUrl, privateKey);
          console.log(JSON.stringify(result));
          break;

        case 'create-wallet':
          const mnemonic = args[1];
          const password = args[2] || 'defaultPassword';
          const walletResult = await wrapper.createWallet(mnemonic, password);
          console.log(JSON.stringify(walletResult));
          break;

        case 'load-wallet':
          const loadMnemonic = args[1];
          const loadPassword = args[2] || 'defaultPassword';
          const loadResult = await wrapper.loadWallet(loadMnemonic, loadPassword);
          console.log(JSON.stringify(loadResult));
          break;

        case 'balances':
          const balancesResult = await wrapper.getBalances();
          console.log(JSON.stringify(balancesResult));
          break;

        case 'shield':
          const tokenAddress = args[1];
          const amount = args[2];
          const gasPrice = args[3];
          const shieldResult = await wrapper.shieldTokens(tokenAddress, amount, gasPrice);
          console.log(JSON.stringify(shieldResult));
          break;

        case 'unshield':
          const unshieldToken = args[1];
          const unshieldAmount = args[2];
          const recipient = args[3];
          const unshieldGasPrice = args[4];
          const unshieldResult = await wrapper.unshieldTokens(unshieldToken, unshieldAmount, recipient, unshieldGasPrice);
          console.log(JSON.stringify(unshieldResult));
          break;

        case 'transfer':
          const transferToken = args[1];
          const transferAmount = args[2];
          const transferRecipient = args[3];
          const transferGasPrice = args[4];
          const transferResult = await wrapper.privateTransfer(transferToken, transferAmount, transferRecipient, transferGasPrice);
          console.log(JSON.stringify(transferResult));
          break;

        case 'history':
          const historyResult = await wrapper.getTransactionHistory();
          console.log(JSON.stringify(historyResult));
          break;

        case 'scan':
          const scanResult = await wrapper.scanNetwork();
          console.log(JSON.stringify(scanResult));
          break;

        default:
          console.log(JSON.stringify({
            success: false,
            error: 'Unknown command',
            available: ['init', 'create-wallet', 'load-wallet', 'balances', 'shield', 'unshield', 'transfer', 'history', 'scan']
          }));
      }
    } catch (error) {
      console.log(JSON.stringify({ success: false, error: error.message }));
    } finally {
      await wrapper.cleanup();
      process.exit(0);
    }
  }

  handleCommand();
}