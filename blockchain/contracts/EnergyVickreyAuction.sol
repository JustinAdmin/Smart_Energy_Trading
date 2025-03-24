// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

// Vickrey auction contract for energy trading
// Based on the sealed-bid auction mechanism
// Auction consists of two phases: bidding and revealing
// Bidders submit sealed bids during the bidding phase
// Bidders reveal their actual bids during the revealing phase
// The highest bidder wins and pays the second highest bid amount
// The seller receives the second highest bid amount
// Non-winning bidders receive a refund of their deposit

// run: truffle console  : to interact with the contract if needed.
// run: truffle migrate --reset : to deploy the contract
// copy contract address into test file to interact with the contract shown below
/*
   Replacing 'EnergyVickreyAuction'
   --------------------------------
   > transaction hash:    0x8b09795334272b3460266e72a0f72cd7391b268b03a3fdf7b82d57d0e2b6270a
   > Blocks: 0            Seconds: 0
   > contract address:    0xA53ae56ce023293693D3a74a3c6d459a80a4c07E
   > block number:        3
   > block timestamp:     1742845923
*/


contract EnergyVickreyAuction {
    struct Bid {
        bytes32 sealedBid;
        uint256 deposit;
    }

    address public seller;
    uint256 public biddingEnd;
    uint256 public revealEnd;
    bool public ended;

    mapping(address => Bid) public bids;
    address[] public bidders;

    address public highestBidder;
    uint256 public highestBid;
    uint256 public secondHighestBid;

    event BidPlaced(address indexed bidder, uint256 deposit);
    event BidRevealed(address indexed bidder, uint256 value);
    event AuctionEnded(address winner, uint256 winningBid);
    event AuctionReset(); // New event for auction reset

    modifier onlyBefore(uint256 _time) {
        require(block.timestamp < _time, "Too late");
        _;
    }

    modifier onlyAfter(uint256 _time) {
        require(block.timestamp > _time, "Too early");
        _;
    }

    modifier auctionNotEnded() {
        require(!ended, "Auction already ended");
        _;
    }

    // Constructor with configurable auction times
    constructor(uint _biddingTime, uint _revealTime) {
        biddingEnd = block.timestamp + _biddingTime;  // Bidding phase ends after specified time
        revealEnd = biddingEnd + _revealTime;         // Reveal phase ends after specified reveal time
        seller = msg.sender; // Set the seller to the contract creator
    }

    // Submit a sealed bid during the bidding phase
    function bid(bytes32 _sealedBid) external payable onlyBefore(biddingEnd) {
        require(bids[msg.sender].sealedBid == bytes32(0), "Already bid");
        require(msg.value > 0, "Deposit must be greater than 0");

        bids[msg.sender] = Bid({
            sealedBid: _sealedBid,
            deposit: msg.value
        });
        bidders.push(msg.sender);

        emit BidPlaced(msg.sender, msg.value);
    }

    // Reveal the actual bid during the reveal phase
    function reveal(uint256 _value, string calldata _nonce)
        external
        onlyAfter(biddingEnd)
        onlyBefore(revealEnd)
    {
        Bid storage bidToCheck = bids[msg.sender];
        require(bidToCheck.sealedBid != bytes32(0), "No bid found");

        // hashing method
        require(
            bidToCheck.sealedBid == keccak256(abi.encodePacked(_value, _nonce)),
            "Invalid bid reveal"
        );
        require(bidToCheck.deposit >= _value, "Deposit too low");

        if (_value > highestBid) {
            secondHighestBid = highestBid;
            highestBid = _value;
            highestBidder = msg.sender;
        } else if (_value > secondHighestBid) {
            secondHighestBid = _value;
        }

        emit BidRevealed(msg.sender, _value);
    }

    // Finalize the auction and distribute funds after the reveal phase ends
    function finalizeAuction() external onlyAfter(revealEnd) auctionNotEnded {
        ended = true;

        if (highestBidder != address(0)) {
            // Transfer the second highest bid amount to the seller
            payable(seller).transfer(secondHighestBid);

            // Refund the highest bidder's deposit minus the second highest bid
            payable(highestBidder).transfer(
                bids[highestBidder].deposit - secondHighestBid
            );
        }

        // Refund all non-winning bidders
        for (uint256 i = 0; i < bidders.length; i++) {
            address bidder = bidders[i];
            if (bidder != highestBidder) {
                uint256 refundAmount = bids[bidder].deposit;
                bids[bidder].deposit = 0; // Prevent re-entrancy
                if (refundAmount > 0) {
                    payable(bidder).transfer(refundAmount);
                }
            }
        }

        emit AuctionEnded(highestBidder, secondHighestBid);
    }

    // Reset the auction state for the next auction
    function resetAuction(uint _biddingTime, uint _revealTime) external {
        //require(ended, "Auction must be ended before resetting");

        // Reset state variables
        biddingEnd = block.timestamp + _biddingTime;
        revealEnd = biddingEnd + _revealTime;
        ended = false;
        highestBidder = address(0);
        highestBid = 0;
        secondHighestBid = 0;
        
        // Clear bidders and bids
        for (uint256 i = 0; i < bidders.length; i++) {
            delete bids[bidders[i]];
        }
        delete bidders;

        emit AuctionReset();
    }
}
